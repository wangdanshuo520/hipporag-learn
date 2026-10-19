"""Run unchanged upstream algorithms with explicit, documented model substitution.

Default: 3 public documents / 1 question. No industrial or private data is sent.
Gold answers/evidence are passed only to upstream evaluation, never to model prompts.
"""
import argparse
import dataclasses
import hashlib
import json
import logging
from pathlib import Path
import sqlite3
import socket
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit
from common import ROOT, UPSTREAM, load_environment, local_config, public_config, require_key


def serialize(obj):
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    if hasattr(obj, "tolist"):
        return obj.tolist()
    raise TypeError(type(obj).__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["deepseek", "local"], default="deepseek")
    parser.add_argument("--method", choices=["hipporag", "standard"], default="hipporag")
    parser.add_argument("--dataset", choices=["sample", "musique", "hotpotqa", "2wikimultihopqa"], default="sample")
    parser.add_argument("--dataset-dir", type=Path, help="Prepared corpus directory; requires manifest.json")
    parser.add_argument("--reuse-llm-cache", type=Path, help="Copy raw response cache; request keys include complete generation settings")
    parser.add_argument("--local-structured", action="store_true", help="Opt-in strict JSON prompts, lossless list-shape normalization, one format retry, repetition penalty 1.1")
    parser.add_argument("--per-query", action="store_true", help="Checkpoint each query and record latency")
    parser.add_argument("--limit", type=int, help="Limit questions only; the FULL retrieval corpus remains unchanged")
    parser.add_argument("--allow-large-index", action="store_true", help="Explicitly enable indexing thousands of documents")
    args = parser.parse_args()
    load_environment()
    if args.backend == "deepseek":
        require_key()
    if args.dataset != "sample" and args.dataset_dir is None and not args.allow_large_index:
        parser.error("Full corpus indexing can be expensive. Inspect the corpus first, then pass --allow-large-index.")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if args.local_structured and args.backend != "local":
        parser.error("--local-structured is local-only")
    cfg = public_config() if args.backend == "deepseek" else local_config()
    if args.backend == "deepseek" and cfg["thinking"] not in {"enabled", "disabled"}:
        parser.error("DEEPSEEK_THINKING must be enabled or disabled")
    if args.backend == "local":
        endpoint = urlsplit(cfg["base_url"])
        if endpoint.scheme != "http" or endpoint.hostname not in {"localhost", "127.0.0.1", "::1"} or endpoint.path.rstrip("/") != "/v1":
            parser.error("LOCAL_BASE_URL must be a local HTTP /v1 endpoint")
        try:
            with socket.create_connection((endpoint.hostname, endpoint.port or 8080), timeout=2):
                pass
        except OSError:
            parser.error("Local Qwen server is not running. Start VS Code task 5 first.")
    from hipporag import HippoRAG
    from hipporag.StandardRAG import StandardRAG
    from hipporag.utils.config_utils import BaseConfig
    sys.path.insert(0, str(UPSTREAM))
    from main import get_gold_docs, get_gold_answers
    dataset_dir = args.dataset_dir.resolve() if args.dataset_dir else UPSTREAM / "reproduce" / "dataset"
    if args.dataset_dir and not (dataset_dir / "manifest.json").exists():
        parser.error("Prepared dataset directory requires manifest.json")
    corpus_file = dataset_dir / f"{args.dataset}_corpus.json"
    question_file = dataset_dir / f"{args.dataset}.json"
    corpus = json.loads(corpus_file.read_text())
    samples = json.loads(question_file.read_text())
    if args.dataset_dir:
        manifest = json.loads((dataset_dir / "manifest.json").read_text())
        for path in (corpus_file, question_file):
            assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest["output_sha256"][path.name], "Subset integrity mismatch"
    if len(corpus) > 1000 and not args.allow_large_index:
        parser.error("More than 1000 documents requires --allow-large-index")
    if args.limit:
        samples = samples[:args.limit]
    docs = [f"{d['title']}\n{d['text']}" for d in corpus]
    queries = [s["question"] for s in samples]
    identity = {**cfg, "backend": args.backend, "method": args.method, "dataset": args.dataset,
                "question_limit": args.limit, "per_query": args.per_query,
                "source_commit": json.loads((ROOT / "reports/source_manifest.json").read_text())["commit"],
                "corpus_sha256": hashlib.sha256(corpus_file.read_bytes()).hexdigest(),
                "questions_sha256": hashlib.sha256(question_file.read_bytes()).hexdigest()}
    if args.local_structured:
        identity["local_adapter"] = {"version":"strict-json-v3", "sha256":hashlib.sha256((ROOT/"scripts/local_extraction_adapter.py").read_bytes()).hexdigest(), "repetition_penalty":1.1, "repetition_context_size":256}
    model_manifest = ROOT / "reports/embedding_download.json"
    if not model_manifest.exists():
        raise SystemExit("Prepare the local embedding first: .venv/bin/python scripts/prepare_embedding.py")
    snapshot = json.loads(model_manifest.read_text())
    if snapshot["model_id"] != cfg["embedding"]:
        raise SystemExit("Embedding configuration changed. Run scripts/prepare_embedding.py again.")
    if not __import__("pathlib").Path(snapshot["snapshot_path"]).is_dir():
        raise SystemExit("Pinned embedding snapshot is missing. Run scripts/prepare_embedding.py again.")
    identity["embedding_snapshot"] = snapshot
    if args.backend == "local":
        local_manifest = ROOT / "reports/local_model_download.json"
        if not local_manifest.exists():
            raise SystemExit("Prepare local Qwen first: .venv/bin/python scripts/prepare_local_model.py")
        model_snapshot = json.loads(local_manifest.read_text())
        if model_snapshot["model_id"] != cfg["model_id"] or not __import__("pathlib").Path(model_snapshot["snapshot_path"]).is_dir():
            raise SystemExit("Local Qwen snapshot is missing or differs from LOCAL_MODEL. Run scripts/prepare_local_model.py again.")
        identity["local_model_snapshot"] = {k: model_snapshot[k] for k in ("model_id", "revision", "weights_sha256")}
    run_id = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:12]
    run_dir = ROOT / "runs" / f"{args.dataset}-{args.method}-{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    cache_reuse = None
    if args.reuse_llm_cache:
        source = args.reuse_llm_cache.resolve()
        if not source.is_file(): parser.error("Raw response cache not found")
        dest = run_dir / "index/llm_cache" / (cfg["llm"].replace("/", "_")+"_cache.sqlite")
        dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists(): parser.error("Destination cache already exists; rerun without --reuse-llm-cache")
        with sqlite3.connect(f"file:{source}?mode=ro",uri=True) as src, sqlite3.connect(dest) as dst:
            src.backup(dst)
        cache_reuse = {"source":str(source),"sha256":hashlib.sha256(source.read_bytes()).hexdigest()}
    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(), logging.FileHandler(run_dir / "run.log")])
    config = BaseConfig(
        save_dir=str(run_dir / "index"), llm_name=cfg["llm"], llm_base_url=cfg["base_url"],
        llm_api_key_env="DEEPSEEK_API_KEY" if args.backend == "deepseek" else None,
        embedding_model_name=snapshot["snapshot_path"],
        embedding_provider="transformers", embedding_batch_size=8,
        retrieval_top_k=200, linking_top_k=5, qa_top_k=5, max_retry_attempts=1,
        rerank_dspy_file_path=str(UPSTREAM / "src/hipporag/prompts/dspy_prompts/filter_llama3.3-70B-Instruct.json"),
    )
    result = {"status": "started", "scope": "model-substituted functional baseline, not paper-score reproduction",
              "started_at": datetime.now(timezone.utc).isoformat(), "config": identity,
              "raw_cache_reuse":cache_reuse, "documents": len(docs), "questions": len(queries), "question_limit": args.limit}
    (run_dir / "result.json").write_text(json.dumps(result, indent=2))
    start = time.perf_counter()
    rag_class = HippoRAG if args.method == "hipporag" else StandardRAG
    try:
        with rag_class(global_config=config) as rag:
            if args.backend == "deepseek":
                # Provider-only setting, included in response cache keys.
                seen = set()
                for attr in ("llm_model", "extraction_llm", "qa_llm"):
                    llm = getattr(rag, attr, None)
                    if llm is not None and id(llm) not in seen:
                        llm.llm_config.generate_params["extra_body"] = {"thinking": {"type": cfg["thinking"]}}
                        seen.add(id(llm))
            if args.local_structured:
                seen=set()
                for attr in ("llm_model", "extraction_llm", "qa_llm"):
                    llm=getattr(rag,attr,None)
                    if llm is not None and id(llm) not in seen:
                        llm.llm_config.generate_params["extra_body"]={"repetition_penalty":1.1,"repetition_context_size":256}
                        seen.add(id(llm))
                if args.method == "hipporag":
                    from local_extraction_adapter import LocalExtractionAdapter
                    rag.openie.llm_model=LocalExtractionAdapter(rag.openie.llm_model,run_dir/"extraction_attempts.jsonl")
            rag.index(docs)
            indexed = time.perf_counter()
            if args.per_query:
                solutions, responses, metadata, per_question = [], [], [], []
                gold_docs = get_gold_docs(samples, args.dataset)
                gold_answers = get_gold_answers(samples)
                for i, query in enumerate(queries):
                    t = time.perf_counter()
                    sol, resp, meta, retr, qa = rag.rag_qa([query], gold_docs=[gold_docs[i]], gold_answers=[gold_answers[i]])
                    solutions.extend(sol); responses.extend(resp); metadata.extend(meta)
                    per_question.append({"id": samples[i].get("id", str(i)), "seconds": time.perf_counter()-t,
                                         "retrieval": retr, "qa": qa})
                    result.update(status="querying", completed_questions=i+1, solutions=solutions,
                                  response_metadata=metadata, per_question=per_question)
                    (run_dir / "result.json").write_text(json.dumps(result,default=serialize,ensure_ascii=False,indent=2))
                    print(f"CHECKPOINT {i+1}/{len(queries)}", flush=True)
                retrieval_metrics = {k: sum(p["retrieval"][k] for p in per_question)/len(per_question) for k in per_question[0]["retrieval"]}
                qa_metrics = {k: sum(p["qa"][k] for p in per_question)/len(per_question) for k in per_question[0]["qa"]}
            else:
                solutions, responses, metadata, retrieval_metrics, qa_metrics = rag.rag_qa(
                    queries, gold_docs=get_gold_docs(samples, args.dataset), gold_answers=get_gold_answers(samples))
            result.update(status="completed", indexing_seconds=indexed-start, qa_seconds=time.perf_counter()-indexed,
                          solutions=solutions, response_metadata=metadata, retrieval_metrics=retrieval_metrics,
                          qa_metrics=qa_metrics)
            if args.method == "hipporag":
                result["graph_info"] = rag.get_graph_info()
                result["queries_with_graph_seeds"] = sum(bool(getattr(s, "graph_seeds", None)) for s in solutions)
                result["note"] = "Check graph seeds and run.log: empty facts can trigger a dense-retrieval fallback."
    except Exception as exc:
        result.update(status="failed",error_type=type(exc).__name__,error=str(exc),elapsed_seconds=time.perf_counter()-start)
        (run_dir / "result.json").write_text(json.dumps(result,default=serialize,ensure_ascii=False,indent=2))
        raise
    usage = []
    for db in (run_dir / "index/llm_cache").glob("*.sqlite"):
        with sqlite3.connect(db) as con:
            usage.extend(json.loads(row[0]) for row in con.execute("SELECT metadata FROM cache"))
    result["cached_unique_response_usage"] = {"requests":len(usage), **{
        key:sum(int(row.get(key) or 0) for row in usage)
        for key in ("prompt_tokens", "completion_tokens", "total_tokens", "cached_tokens")}}
    result["usage_note"] = "Distinct cached responses, not a per-invocation bill; reruns reuse caches."
    (run_dir / "result.json").write_text(json.dumps(result, default=serialize, ensure_ascii=False, indent=2))
    print(json.dumps({"result": str(run_dir / "result.json"), "retrieval": retrieval_metrics, "qa": qa_metrics}, indent=2))


if __name__ == "__main__":
    main()

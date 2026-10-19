"""Run local diagnostic baselines on the source-checked PF525 set.

No hosted LLM endpoint is used. The local Qwen server must be running first.
"""
import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

from common import ROOT, UPSTREAM, load_environment, local_config

sys.path.insert(0, str(UPSTREAM / "src"))

DATA = ROOT / "data" / "industrial_pf525"
OUT = ROOT / "runs" / "industrial_pf525_local"
ACTION_RE = re.compile(r"\b(?:ASK_FAULT_CODE|NO_EVIDENCE|CHECK_[A-Z0-9_]+)\b")


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def load_data():
    manifest = json.loads((DATA / "manifest.json").read_text())
    for name, digest in manifest["sha256"].items():
        assert hashlib.sha256((DATA / name).read_bytes()).hexdigest() == digest, name
    cards = json.loads((DATA / "corpus.json").read_text())
    cases = json.loads((DATA / "cases.json").read_text())
    return manifest, cards, cases


def normalize_retrieval(solutions, docs_to_ids):
    return [{"case_id": s.question, "doc_ids": [docs_to_ids[d] for d in s.docs],
             "scores": [float(x) for x in s.doc_scores]} for s in solutions]


def build_config(save_dir, snapshot, cfg):
    from hipporag.utils.config_utils import BaseConfig
    return BaseConfig(
        save_dir=str(save_dir), llm_name=cfg["llm"], llm_base_url=cfg["base_url"],
        llm_api_key_env=None, embedding_model_name=snapshot["snapshot_path"],
        embedding_provider="transformers", embedding_batch_size=8,
        retrieval_top_k=24, linking_top_k=5, qa_top_k=5, max_retry_attempts=1,
        rerank_dspy_file_path=str(UPSTREAM / "src/hipporag/prompts/dspy_prompts/filter_llama3.3-70B-Instruct.json"),
    )


def run_retrieval(method, cards, cases, snapshot, cfg):
    from hipporag import HippoRAG
    from hipporag.StandardRAG import StandardRAG
    from local_extraction_adapter import LocalExtractionAdapter

    outfile = OUT / f"{method}_retrieval.json"
    prior = json.loads(outfile.read_text()) if outfile.exists() else {"method": method, "rows": [], "status": "started"}
    done = {row["case_id"] for row in prior["rows"]}
    docs = [f"{c['title']}\n{c['text']}" for c in cards]
    docs_to_ids = dict(zip(docs, (c["id"] for c in cards)))
    klass = HippoRAG if method == "hippo" else StandardRAG
    with klass(global_config=build_config(OUT / method / "index", snapshot, cfg)) as rag:
        seen = set()
        for attr in ("llm_model", "extraction_llm", "qa_llm"):
            llm = getattr(rag, attr, None)
            if llm is not None and id(llm) not in seen:
                llm.llm_config.generate_params["extra_body"] = {"repetition_penalty": 1.1, "repetition_context_size": 256}
                seen.add(id(llm))
        if method == "hippo":
            rag.openie.llm_model = LocalExtractionAdapter(rag.openie.llm_model, OUT / "hippo" / "extraction_attempts.jsonl")
        rag.index(docs)
        if method == "hippo":
            prior["graph_info"] = rag.get_graph_info()
        for i, case in enumerate(cases, 1):
            if case["id"] in done:
                continue
            start = time.perf_counter()
            solution = rag.retrieve([case["question"]], num_to_retrieve=len(cards))[0]
            prior["rows"].append({"case_id": case["id"], "doc_ids": [docs_to_ids[d] for d in solution.docs],
                                  "scores": [float(x) for x in solution.doc_scores],
                                  "seconds": time.perf_counter() - start,
                                  "graph_seed_count": len(getattr(solution, "graph_seeds", None) or [])})
            save(outfile, prior)
            print(f"RETRIEVAL {method} {i}/{len(cases)} {case['id']}", flush=True)
    prior["status"] = "completed"
    save(outfile, prior)


def filtered_ids(raw_ids, cards_by_id, observed_state):
    code = observed_state.get("fault_code")
    model = observed_state.get("model")
    return [doc_id for doc_id in raw_ids if cards_by_id[doc_id]["metadata"]["model"] == model and
            (code is None or cards_by_id[doc_id]["metadata"]["fault_code"] == code)][:5]


def prompt(case, selected, cards_by_id, condition_prompt):
    excerpts = "\n".join(f"[{i+1}] {cards_by_id[doc_id]['text']}" for i, doc_id in enumerate(selected)) or "(none)"
    instruction = (
        "You are classifying a maintenance information request, not operating equipment. "
        "Choose exactly one diagnostic action ID shown in the excerpts, ASK_FAULT_CODE, or NO_EVIDENCE. "
        "Return only the ID. Never invent an action ID. If no excerpt supports an action, choose NO_EVIDENCE."
    )
    if condition_prompt:
        instruction += (
            " Check the observed model and fault code against each excerpt before choosing. "
            "A mismatching fault code is inapplicable. If the fault code is missing and multiple actions remain plausible, "
            "choose ASK_FAULT_CODE. If evidence is absent even after the code is known, choose NO_EVIDENCE."
        )
    user = f"Question: {case['question']}\nObserved state: {json.dumps(case['observed_state'])}\nGuide excerpts:\n{excerpts}"
    return [{"role": "system", "content": instruction}, {"role": "user", "content": user}]


def run_generation(cards, cases, cfg):
    from openai import OpenAI
    cards_by_id = {c["id"]: c for c in cards}
    retrieval = {method: {row["case_id"]: row for row in json.loads((OUT / f"{method}_retrieval.json").read_text())["rows"]}
                 for method in ("dense", "hippo")}
    outfile = OUT / "baseline_results.json"
    result = json.loads(outfile.read_text()) if outfile.exists() else {"status": "started", "rows": []}
    done = {(row["arm"], row["case_id"]) for row in result["rows"]}
    arms = ("dense", "hippo", "metadata_filter", "prompt_only", "metadata_plus_prompt")
    with OpenAI(api_key="local-placeholder", base_url=cfg["base_url"], timeout=240, max_retries=0) as client:
        for arm in arms:
            method = "hippo" if arm == "hippo" else "dense"
            for i, case in enumerate(cases, 1):
                if (arm, case["id"]) in done:
                    continue
                raw_ids = retrieval[method][case["id"]]["doc_ids"]
                selected = filtered_ids(raw_ids, cards_by_id, case["observed_state"]) if arm in ("metadata_filter", "metadata_plus_prompt") else raw_ids[:5]
                start = time.perf_counter()
                response = client.chat.completions.create(
                    model=cfg["llm"], messages=prompt(case, selected, cards_by_id, arm in ("prompt_only", "metadata_plus_prompt")),
                    max_completion_tokens=80, temperature=0,
                    extra_body={"repetition_penalty": 1.1, "repetition_context_size": 256},
                )
                answer = response.choices[0].message.content or ""
                match = ACTION_RE.search(answer)
                predicted = match.group(0) if match else "INVALID_OUTPUT"
                allowed = {cards_by_id[d]["metadata"]["action_id"] for d in selected} | {"ASK_FAULT_CODE", "NO_EVIDENCE"}
                if predicted not in allowed:
                    predicted = "INVALID_OUTPUT"
                row = {"arm": arm, "case_id": case["id"], "split": case["split"],
                       "gold": case["gold_decision"], "prediction": predicted, "raw_response": answer,
                       "selected_doc_ids": selected, "gold_evidence_ids": case["gold_evidence_ids"],
                       "seconds": time.perf_counter() - start,
                       "usage": response.usage.model_dump() if response.usage else None,
                       "response_model": response.model}
                result["rows"].append(row)
                save(outfile, result)
                print(f"ANSWER {arm} {i}/{len(cases)} {case['id']} {predicted}", flush=True)
    result["status"] = "completed"
    save(outfile, result)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("all", "dense", "hippo", "generation"), default="all")
    args = parser.parse_args()
    load_environment()
    cfg = local_config()
    if cfg["base_url"] != "http://127.0.0.1:8080/v1":
        parser.error("This diagnostic script only allows the pinned local loopback endpoint")
    manifest, cards, cases = load_data()
    snapshot = json.loads((ROOT / "reports/embedding_download.json").read_text())
    assert Path(snapshot["snapshot_path"]).is_dir()
    OUT.mkdir(parents=True, exist_ok=True)
    save(OUT / "run_config.json", {"dataset_sha256": manifest["sha256"], "llm": cfg["model_id"],
                                  "embedding": snapshot["model_id"], "backend": "local-only", "top_k": 5,
                                  "hippo_extraction_adapter": "strict-json-v3"})
    if args.phase in ("all", "dense"):
        run_retrieval("dense", cards, cases, snapshot, cfg)
    if args.phase in ("all", "hippo"):
        run_retrieval("hippo", cards, cases, snapshot, cfg)
    if args.phase in ("all", "generation"):
        run_generation(cards, cases, cfg)


if __name__ == "__main__":
    main()

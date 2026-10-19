"""Real local embeddings + dense ranking + upstream recall evaluator; no LLM/API."""
import json
import sys
from common import ROOT, UPSTREAM, load_environment


def main():
    load_environment()
    from hipporag.embedding_model.Transformers import TransformersEmbeddingModel
    from hipporag.utils.config_utils import BaseConfig
    from hipporag.evaluation.retrieval_eval import RetrievalRecall
    import numpy as np
    sys.path.insert(0, str(UPSTREAM))
    from main import get_gold_docs
    snapshot = json.loads((ROOT / "reports/embedding_download.json").read_text())
    data = UPSTREAM / "reproduce/dataset"
    corpus = json.loads((data / "sample_corpus.json").read_text())
    samples = json.loads((data / "sample.json").read_text())
    docs = [f"{d['title']}\n{d['text']}" for d in corpus]
    queries = [s["question"] for s in samples]
    cfg = BaseConfig(embedding_model_name=snapshot["snapshot_path"], embedding_batch_size=8)
    model = TransformersEmbeddingModel(cfg, snapshot["snapshot_path"])
    scores = model.batch_encode(queries) @ model.batch_encode(docs).T
    ranked = [[docs[i] for i in np.argsort(-row)] for row in scores]
    metrics, _ = RetrievalRecall().calculate_metric_scores(get_gold_docs(samples, "sample"), ranked, [1, 2, 3])
    report = {"scope": "real local dense retrieval smoke check only; no graph or generation",
              "documents": len(docs), "questions": len(queries), "embedding": snapshot,
              "metrics": metrics, "ranked_titles": [[d.split('\n', 1)[0] for d in row] for row in ranked]}
    (ROOT / "reports/local_retrieval_check.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

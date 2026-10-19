"""Download a pinned public model snapshot and verify real CPU embeddings."""
import hashlib
import json
from common import ROOT, load_environment, public_config


def main():
    load_environment()
    from huggingface_hub import HfApi, snapshot_download
    from sentence_transformers import SentenceTransformer
    import numpy as np
    model_id = public_config()["embedding"]
    manifest = ROOT / "reports/embedding_download.json"
    old = json.loads(manifest.read_text()) if manifest.exists() else {}
    revision = old.get("revision") if old.get("model_id") == model_id else None
    if revision is None:
        revision = HfApi().model_info(model_id).sha
    path = snapshot_download(model_id, revision=revision,
                             allow_patterns=["*.json", "*.txt", "*.safetensors", "1_Pooling/*"], max_workers=2)
    model = SentenceTransformer(path, device="cpu")
    vectors = model.encode(["Alice works at Acme.", "Acme is located in Paris."], normalize_embeddings=True)
    assert vectors.shape[0] == 2 and np.isfinite(vectors).all()
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-5)
    report = {"model_id": model_id, "revision": revision, "snapshot_path": path,
              "device": "cpu", "shape": list(vectors.shape), "finite_and_normalized": True,
              "weight_sha256": {}}
    from pathlib import Path
    for file in Path(path).rglob("*.safetensors"):
        report["weight_sha256"][str(file.relative_to(path))] = hashlib.sha256(file.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

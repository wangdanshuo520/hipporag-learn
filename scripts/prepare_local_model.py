"""Download a pinned MLX Qwen snapshot for a reproducible local LLM backend."""
import hashlib
import json
from pathlib import Path
from common import ROOT, load_environment, local_config


def main():
    load_environment()
    from huggingface_hub import HfApi, snapshot_download

    model_id = local_config()["model_id"]
    manifest = ROOT / "reports/local_model_download.json"
    old = json.loads(manifest.read_text()) if manifest.exists() else {}
    revision = old.get("revision") if old.get("model_id") == model_id else None
    if revision is None:
        revision = HfApi().model_info(model_id).sha
    path = Path(snapshot_download(
        model_id, revision=revision,
        allow_patterns=["*.json", "*.safetensors", "*.model", "*.tiktoken"],
        max_workers=2,
    ))
    weights = sorted(path.glob("*.safetensors"))
    if not weights or not (path / "config.json").exists() or not (path / "tokenizer_config.json").exists():
        raise SystemExit("Incomplete MLX model snapshot")
    report = {
        "model_id": model_id, "revision": revision, "snapshot_path": str(path),
        "weights_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in weights},
    }
    manifest.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

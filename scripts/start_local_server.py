"""Run pinned local Qwen over an OpenAI-compatible loopback endpoint."""
import ipaddress
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from common import ROOT, load_environment, local_config


def main():
    load_environment()
    cfg = local_config()
    manifest_file = ROOT / "reports/local_model_download.json"
    if not manifest_file.exists():
        raise SystemExit("Prepare Qwen first: .venv/bin/python scripts/prepare_local_model.py")
    manifest = json.loads(manifest_file.read_text())
    if cfg["model_id"] != manifest["model_id"] or not Path(manifest["snapshot_path"]).is_dir():
        raise SystemExit("LOCAL_MODEL does not match the downloaded snapshot")
    url = urlsplit(cfg["base_url"])
    hostname = url.hostname or ""
    if url.scheme != "http" or url.path.rstrip("/") != "/v1" or hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise SystemExit("LOCAL_BASE_URL must be a local HTTP /v1 endpoint")
    py = ROOT / ".venv-local/bin/python"
    if not py.exists():
        raise SystemExit("Install MLX LM in .venv-local first")
    argv = [str(py), "-m", "mlx_lm", "server", "--model", manifest["snapshot_path"],
            "--host", hostname, "--port", str(url.port or 8080),
            "--decode-concurrency", "1", "--prompt-concurrency", "1"]
    print("Starting pinned Qwen on", cfg["base_url"], flush=True)
    os.execv(str(py), argv)


if __name__ == "__main__":
    main()

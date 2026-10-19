import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "vendor" / "HippoRAG-main"


def load_environment():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)
    os.environ.setdefault("HF_HOME", str(ROOT / ".cache" / "huggingface"))
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
    os.environ.setdefault("TIKTOKEN_CACHE_DIR", str(ROOT / ".cache" / "tiktoken"))


def require_key():
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not key or key.lower() in {"your-key", "your_api_key", "sk-..."}:
        raise SystemExit("Missing DEEPSEEK_API_KEY. Fill the local .env file; do not paste the key into chat.")


def public_config():
    return {
        "llm": os.environ.get("DEEPSEEK_MODEL", "deepseek-flash"),
        "base_url": os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        "embedding": os.environ.get("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"),
        "thinking": os.environ.get("DEEPSEEK_THINKING", "disabled"),
    }


def local_config():
    return {
        # MLX maps this request name to the pinned --model snapshot passed to its server.
        "llm": "default_model",
        "model_id": os.environ.get("LOCAL_MODEL", "mlx-community/Qwen2.5-1.5B-Instruct-4bit"),
        "base_url": os.environ.get("LOCAL_BASE_URL", "http://127.0.0.1:8080/v1"),
        "embedding": os.environ.get("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"),
    }

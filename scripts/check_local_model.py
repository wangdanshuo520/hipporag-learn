"""Exercise the local Qwen endpoint and verify nonempty text plus token usage."""
import json
from datetime import datetime, timezone
from common import ROOT, load_environment, local_config


def main():
    load_environment()
    from openai import OpenAI
    cfg = local_config()
    with OpenAI(api_key="local-placeholder", base_url=cfg["base_url"], timeout=180, max_retries=0) as client:
        response = client.chat.completions.create(
            model=cfg["llm"], messages=[{"role": "user", "content": "Reply with exactly OK."}],
            max_completion_tokens=16, temperature=0,
        )
    text = response.choices[0].message.content or ""
    usage = response.usage
    if not text.strip() or usage is None or usage.prompt_tokens is None or usage.completion_tokens is None:
        raise SystemExit("Local endpoint returned empty text or missing token usage")
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "model_id": cfg["model_id"],
              "base_url": cfg["base_url"], "response_model": response.model,
              "answer": text, "usage": usage.model_dump()}
    (ROOT / "reports/local_model_check.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

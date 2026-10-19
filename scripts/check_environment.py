"""Offline by default. --api sends one small chat completion to DeepSeek."""
import argparse
import importlib.metadata
import json
import os
import platform
import sys
from common import ROOT, load_environment, public_config, require_key


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", action="store_true")
    args = parser.parse_args()
    load_environment()
    report = {"python": sys.version.split()[0], "platform": platform.platform(),
              "key_configured": bool(os.environ.get("DEEPSEEK_API_KEY", "").strip()),
              "models": public_config(), "packages": {}}
    for package in ["hipporag", "torch", "transformers", "sentence-transformers", "openai", "python-dotenv"]:
        try:
            report["packages"][package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            report["packages"][package] = "MISSING"
    import torch
    from hipporag import HippoRAG
    report["hipporag_import"] = True
    report["mps_available"] = torch.backends.mps.is_available()
    report["cuda_available"] = torch.cuda.is_available()
    report["embedding_device"] = "cpu (upstream Transformers backend on this Mac)"
    if args.api:
        require_key()
        from openai import OpenAI
        cfg = public_config()
        with OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url=cfg["base_url"], timeout=60, max_retries=1) as client:
            response = client.chat.completions.create(
                model=cfg["llm"], messages=[{"role": "user", "content": "Reply with exactly OK."}],
                max_tokens=16, extra_body={"thinking": {"type": cfg["thinking"]}},
            )
        report["api"] = {"response_model": response.model,
                         "nonempty_response": bool(response.choices[0].message.content),
                         "finish_reason": response.choices[0].finish_reason,
                         "usage": response.usage.model_dump() if response.usage else None}
    destination = ROOT / "reports" / ("api_check.json" if args.api else "environment_check.json")
    destination.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

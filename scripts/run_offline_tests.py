"""Run upstream mocked tests; this is NOT a real-model quality evaluation."""
import json
import os
import subprocess
import sys
from common import ROOT, UPSTREAM, load_environment


def main():
    load_environment()
    env = dict(os.environ)
    env["PYTHONPATH"] = str(UPSTREAM / "src")
    report = {"scope": "upstream unit/component tests with mocked model backends", "suites": []}
    for pattern in ["test_openai_sdk_compat.py", "test_hipporag_state_consistency.py", "test_openie_extraction.py"]:
        command = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", pattern, "-v"]
        result = subprocess.run(command, cwd=UPSTREAM, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        log = ROOT / "reports" / (pattern.removesuffix(".py") + ".log")
        log.write_text(result.stdout)
        report["suites"].append({"pattern": pattern, "exit_code": result.returncode, "log": log.name})
        print(pattern, "PASS" if result.returncode == 0 else "FAIL", flush=True)
    report["passed"] = all(s["exit_code"] == 0 for s in report["suites"])
    (ROOT / "reports/offline_tests.json").write_text(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()

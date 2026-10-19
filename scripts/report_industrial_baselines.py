"""Summarize source-checked PF525 local diagnostic baselines."""
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs" / "industrial_pf525_local"


def rate(rows, predicate):
    return sum(predicate(x) for x in rows) / len(rows) if rows else None


def main():
    cases = json.loads((ROOT / "data/industrial_pf525/cases.json").read_text())
    case_by_id = {c["id"]: c for c in cases}
    results = json.loads((RUN / "baseline_results.json").read_text())
    if results["status"] != "completed":
        raise SystemExit("Industrial generation is incomplete; report requires four complete arms")
    expected = {(arm, case["id"]) for arm in ("dense", "hippo", "metadata_filter", "prompt_only", "metadata_plus_prompt") for case in cases}
    assert {(r["arm"], r["case_id"]) for r in results["rows"]} == expected
    output = {"scope": "36 constructed PF525 guide scenarios; local Qwen only; not field validation", "arms": {}}
    for arm in ("dense", "hippo", "metadata_filter", "prompt_only", "metadata_plus_prompt"):
        rows = [r for r in results["rows"] if r["arm"] == arm]
        known = [r for r in rows if not case_by_id[r["case_id"]]["needs_clarification"]]
        unknown = [r for r in rows if case_by_id[r["case_id"]]["needs_clarification"]]
        output["arms"][arm] = {
            "overall_decision_accuracy": rate(rows, lambda r: r["prediction"] == r["gold"]),
            "known_action_accuracy": rate(known, lambda r: r["prediction"] == r["gold"]),
            "unknown_ask_rate": rate(unknown, lambda r: r["prediction"] == "ASK_FAULT_CODE"),
            "known_gold_evidence_at_1": rate(known, lambda r: r["gold_evidence_ids"][0] in r["selected_doc_ids"][:1]),
            "known_gold_evidence_at_5": rate(known, lambda r: r["gold_evidence_ids"][0] in r["selected_doc_ids"][:5]),
            "wrong_action_on_unknown_rate": rate(unknown, lambda r: r["prediction"].startswith("CHECK_")),
            "invalid_output_count": sum(r["prediction"] == "INVALID_OUTPUT" for r in rows),
            "mean_generation_seconds": statistics.mean(r["seconds"] for r in rows),
            "generation_tokens": sum((r["usage"] or {}).get("total_tokens", 0) for r in rows),
            "by_split": {split: {"accuracy": rate([r for r in rows if r["split"] == split], lambda r: r["prediction"] == r["gold"]),
                                  "n": sum(r["split"] == split for r in rows)} for split in ("dev", "test")},
        }
    (ROOT / "reports/industrial_baseline_results.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    def pct(value): return f"{100 * value:.1f}%"
    lines = ["# PowerFlex 525 本地基线诊断结果", "", "36 个从厂商指南构造的案例；只使用本机 Qwen，没有调用 DeepSeek API；尚未经过现场验证。", "",
             "| 方法 | 总决策正确 | 已知码动作正确 | 缺失码追问 | 已知码证据@5 | 缺失码误给动作 |", 
             "|---|---:|---:|---:|---:|---:|"]
    for arm, x in output["arms"].items():
        lines.append(f"| {arm} | {pct(x['overall_decision_accuracy'])} | {pct(x['known_action_accuracy'])} | {pct(x['unknown_ask_rate'])} | {pct(x['known_gold_evidence_at_5'])} | {pct(x['wrong_action_on_unknown_rate'])} |")
    hippo_retrieval = json.loads((RUN / "hippo_retrieval.json").read_text())
    dense_retrieval = json.loads((RUN / "dense_retrieval.json").read_text())
    assert hippo_retrieval["status"] == dense_retrieval["status"] == "completed"
    graph = hippo_retrieval["graph_info"]
    seeded = sum(row["graph_seed_count"] > 0 for row in hippo_retrieval["rows"])
    lines += ["", "同一 24 张卡、36 个构造问题、同一个 Qwen 1.5B 和 BGE 向量模型；每种方法最多给模型 5 张卡。`metadata_filter` 在 dense 排序后按已知型号与故障码硬过滤；`prompt_only` 使用同一 dense 排序，增加条件判断提示。HippoRAG2 使用 strict-json-v3 本地抽取适配。", "",
              "指标定义：已知码动作正确为 24 个已知故障码案例选中手册对应动作标识的比例；缺失码追问为 12 个缺失故障码案例输出 `ASK_FAULT_CODE` 的比例；误给动作为缺失码时仍输出某一具体 `CHECK_...` 的比例。证据@5 只评估已知码案例。", "",
              f"HippoRAG2 索引实际产生 {graph['num_extracted_triples']} 个抽取三元组、{graph['num_total_nodes']} 个图节点；{seeded}/36 次检索有图种子。它的平均检索耗时 {statistics.mean(row['seconds'] for row in hippo_retrieval['rows']):.2f} 秒，dense 为 {statistics.mean(row['seconds'] for row in dense_retrieval['rows']):.3f} 秒。机器可读 JSON 中的 `generation_tokens` 仅是最终动作分类调用，不包含图索引抽取和检索中的模型调用。", "",
              "`metadata_plus_prompt` 组合硬过滤与条件判断提示词，是避免把简单组合误当作新方法的附加强基线。它达到 35/36，唯一错误是 Qwen 把 `CHECK_HEATSINK_COOLING` 拼成 `CHECK_HESTSINK_COOLING`。这说明当前数据的决策问题已基本可由手工结构化 metadata 与简单提示解决。下一步应先增加多手册、多型号、版本边界、互相矛盾和缺证据的案例；在更难的数据上若组合基线仍足够好，就应转向其他研究分支。", "",
              "本实验的故障码 metadata 是人工从手册整理的，不能当成自动抽取能力；开发/测试分组来自同一手册与同一模板，测试集也不能代表跨文档泛化。", "",
              "这是从一份厂商指南构造的流程诊断集，缺少真实工单、专家盲审和独立手册。分数不能证明 Idea 1 的研究增益；它只说明本地对照在这组受控条件下的行为。逐题原始输出、文档排序、耗时和 token 元数据见 `runs/industrial_pf525_local/`。", "",
              "复现：在 VS Code 先运行 `5. Start local Qwen server`，再运行 `Industrial: local baselines`，最后执行 `.venv/bin/python scripts/report_industrial_baselines.py`。数据和模型版本、哈希分别见 `data/industrial_pf525/manifest.json`、`reports/local_model_download.json`、`reports/embedding_download.json` 与 `runs/industrial_pf525_local/run_config.json`。"]
    (ROOT / "reports/industrial_baseline_results.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(output["arms"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

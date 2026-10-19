# PowerFlex 525 本地基线诊断结果

36 个从厂商指南构造的案例；只使用本机 Qwen，没有调用 DeepSeek API；尚未经过现场验证。

| 方法 | 总决策正确 | 已知码动作正确 | 缺失码追问 | 已知码证据@5 | 缺失码误给动作 |
|---|---:|---:|---:|---:|---:|
| dense | 22.2% | 4.2% | 58.3% | 100.0% | 41.7% |
| hippo | 47.2% | 37.5% | 66.7% | 100.0% | 33.3% |
| metadata_filter | 77.8% | 87.5% | 58.3% | 100.0% | 41.7% |
| prompt_only | 69.4% | 54.2% | 100.0% | 100.0% | 0.0% |
| metadata_plus_prompt | 97.2% | 95.8% | 100.0% | 100.0% | 0.0% |

同一 24 张卡、36 个构造问题、同一个 Qwen 1.5B 和 BGE 向量模型；每种方法最多给模型 5 张卡。`metadata_filter` 在 dense 排序后按已知型号与故障码硬过滤；`prompt_only` 使用同一 dense 排序，增加条件判断提示。HippoRAG2 使用 strict-json-v3 本地抽取适配。

指标定义：已知码动作正确为 24 个已知故障码案例选中手册对应动作标识的比例；缺失码追问为 12 个缺失故障码案例输出 `ASK_FAULT_CODE` 的比例；误给动作为缺失码时仍输出某一具体 `CHECK_...` 的比例。证据@5 只评估已知码案例。

HippoRAG2 索引实际产生 82 个抽取三元组、128 个图节点；36/36 次检索有图种子。它的平均检索耗时 1.10 秒，dense 为 0.009 秒。机器可读 JSON 中的 `generation_tokens` 仅是最终动作分类调用，不包含图索引抽取和检索中的模型调用。

`metadata_plus_prompt` 组合硬过滤与条件判断提示词，是避免把简单组合误当作新方法的附加强基线。它达到 35/36，唯一错误是 Qwen 把 `CHECK_HEATSINK_COOLING` 拼成 `CHECK_HESTSINK_COOLING`。这说明当前数据的决策问题已基本可由手工结构化 metadata 与简单提示解决。下一步应先增加多手册、多型号、版本边界、互相矛盾和缺证据的案例；在更难的数据上若组合基线仍足够好，就应转向其他研究分支。

本实验的故障码 metadata 是人工从手册整理的，不能当成自动抽取能力；开发/测试分组来自同一手册与同一模板，测试集也不能代表跨文档泛化。

这是从一份厂商指南构造的流程诊断集，缺少真实工单、专家盲审和独立手册。分数不能证明 Idea 1 的研究增益；它只说明本地对照在这组受控条件下的行为。逐题原始输出、文档排序、耗时和 token 元数据见 `runs/industrial_pf525_local/`。

复现：在 VS Code 先运行 `5. Start local Qwen server`，再运行 `Industrial: local baselines`，最后执行 `.venv/bin/python scripts/report_industrial_baselines.py`。数据和模型版本、哈希分别见 `data/industrial_pf525/manifest.json`、`reports/local_model_download.json`、`reports/embedding_download.json` 与 `runs/industrial_pf525_local/run_config.json`。

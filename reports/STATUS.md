# 本地复现状态 — 更新于 2026-10-17

## 当前工作区：Idea 1 计划任务 1–4 已完成（本轮未用 DeepSeek API）

- 当前工作区为 `/Users/mingyue/Documents/ChatGPT/hipporag-idea1`；从旧工作区迁入历史结果、源码与模型缓存，但没有迁入 `.env` 或 API 密钥。下文关于旧工作区曾配置密钥的记载仅是历史状态。
- 已核查 HippoRAG 2、RuleRAG、TelcoAI、澄清效用、AskBench、SAGE-Agent 的相关性与新颖性风险，见 `idea1_literature_2026-10-17.md`。
- 已选择 PowerFlex 525 故障初步分流，使用厂商指南构造 24 张故障证据卡和 36 个案例，见 `industrial_scenario_pf525.md` 与 `../data/industrial_pf525/`。这些不是现场记录或专家盲审数据。
- 已在本地 Qwen 1.5B + BGE 下完成 dense、HippoRAG2、metadata 硬过滤、条件判断提示词以及两者组合的全部 36 题运行；原始输出在 `../runs/industrial_pf525_local/`，汇总见 `industrial_baseline_results.md`。HippoRAG2 图有 128 节点、82 个抽取三元组，36/36 检索存在图种子。
- 组合基线达到 35/36，显示当前构造集基本被简单方法解决。先扩充困难案例、验证自动 metadata 抽取与跨手册泛化，再判断 Idea 1 是否值得实现更复杂方法。

## 迁移前的历史复现进展

- DeepSeek API 连接检查已通过，`deepseek-flash` 非思考模式调用成功；密钥只保存在本地 `.env`，没有写入报告。
- DeepSeek 的 HippoRAG2 与 dense sample 均完成；sample 的唯一问题存在证据缺口，两个方法回答 F1 均为 0，不将其解释为方法失败或优劣。
- 已完成 sample 证据审查、固定 MuSiQue 50 题/227 文档开发集及完整性校验，并在同一数据和 BGE 向量模型上完成 DeepSeek 与本地 Qwen 的四组 50 题对照。
- DeepSeek HippoRAG2：Recall@5=86.17%、F1=61.05%、EM=52%，抽取 3110 个三元组，图含 2936 节点、7146 边；49/50 个问题有图种子。DeepSeek dense：Recall@5=80%、F1=63.52%、EM=50%。
- 原始 Qwen 1.5B 配置在 NER 阶段因 2/227 解析失败中止；不为此配置报告虚构的评测分数。
- 使用显式 strict-json-v3 抽取接口适配后，完成 HippoRAG 和相同生成参数的 Dense 50 题对照。官方源码未修改，但抽取提示词/格式适配与原始配置不同。
- 本地 Qwen HippoRAG Recall@5=81.17%、F1=14.08%、EM=6%；dense Recall@5=80%、F1=17.36%、EM=6%。结果仅适用于这个缩减语料开发集。
- 原始结果、适配日志、缓存来源、逐题答案、token 和时间统计均已保存。四组对照及解释见 `model_comparison.md`，机器可读结果见 `model_comparison.json`；本地 Qwen 的深入分析见 `dev50_analysis.md`。
- 新增数据检查和适配层检查均通过；Python 脚本和 VS Code JSON 配置校验通过。
- 迁移前尚未开展 Idea 1 算法和工业验证；当前通用问答结果不是完整语料或原论文分数复现。

以下为此前环境与本地 sample 阶段的记录；其中全量数据集和论文分数仍未复现。

## 已完成并验证

- VS Code 项目已打开；微软 Python、Pylance、debugpy 扩展已安装。
- 独立 Python 3.10.22 环境，82 个依赖包；HippoRAG 2.0.0a5、torch 2.5.1、sentence-transformers 3.3.1 导入正常。
- 续接检查：`uv pip check` 确认全部 82 个包依赖兼容；所有项目脚本重新通过 compileall 语法检查，VS Code 已成功展示 README。
- 官方源码固定到 `d5c8329422e0a0b834a15874545cb6a74b4f9b26`；下载的固定提交压缩包逐文件比对无差异。上游算法未修改。
- 官方离线测试 31/31 通过：SDK 兼容 18 项、状态/索引一致性 6 项、OpenIE 抽取组件 7 项。测试使用模拟模型，不证明真实模型效果。
- 本地 BGE-small-en-v1.5 下载成功；固定模型快照与权重 SHA256；CPU 实际编码输出 384 维，有限值与归一化检查通过。
- 官方 sample 的实际本地 dense retrieval 已运行：3 文档、1 问题，Recall@1=0，Recall@2=0，Recall@3=1。正确支持段落排第三。这是极小流程检查，不支持性能结论，也不是 HippoRAG 图检索结果。
- 缺少密钥时，端到端脚本会在发起请求前停止，并提示配置 `.env`；现已完成本地配置和 API 检查。
- VS Code 配置 JSON 和 Python 脚本语法检查通过。
- `RESEARCH.md` 已包含研究假设、源码路径、强基线、数据拆分与否证条件；5 个合成任务样例仅用于任务设计。
- 保留 DeepSeek API 后端，新增 MLX LM 本地 Qwen2.5-1.5B-Instruct-4bit 后端。独立 Python 3.12 环境的 34 个依赖通过兼容检查；模型固定到 Hugging Face 提交 `8b403126fc14f14cfc99bb4cfa72ecbc129ea677`，权重 SHA256 已记录。
- 本地 Qwen 真实接口检查通过：返回 `OK`，包含完整 token 用量字段，无需 DeepSeek 密钥。
- 官方 sample（3 文档、1 问题）本地 HippoRAG2 与 dense 对照均完成。HippoRAG2 抽取 24 个三元组，图含 30 个节点、53 条边，问题有 graph seeds；Recall@1=0、Recall@5=1、回答 F1=0.8、ExactMatch=0。dense 对照 Recall@1=0、Recall@5=1、回答 F1=0、ExactMatch=0。完整配置和答案见 `local_run_summary.json`。样本极小，不能推断性能优势。
- 本次 Qwen 冷运行缓存记录：HippoRAG2 共 8 次 LLM 请求，合计 7572 tokens（输入 6765、输出 807）；dense 共 1 次请求，合计 1145 tokens。这是本地模型的实际用量，不等于 DeepSeek 在相同样例上的用量或费用；本地运行未调用外部模型 API。

## 尚未完成

- 两个后端尚未在完整 MuSiQue 语料和真实工业数据上检验准确率、稳定性与成本。
- 完整语料规模化实验：尚未执行。
- ICML 2025 原论文表格复现：尚未执行；当前代码/模型配置也不等于原论文配置。
- Idea 1 算法实现与真实现场数据验证：尚未开展；本轮公开指南构造案例只属于诊断性实验。

## 下一步

本地 Qwen 可使用 VS Code 任务 `5. Start local Qwen server` 启动服务，再运行对应的 sample 或 Dev50 任务。DeepSeek 可使用 `2. Check DeepSeek API` 和两个 `Dev50: DeepSeek ...` 任务复跑。下一阶段应先确定工业任务的条件字段、标注协议与评价指标，再实现 Idea 1 的适用条件判断和澄清机制。

扩展实验规模时先核对抽取事实、图节点/边、graph_seeds 与回退日志，确认图检索实际起作用。

## 证据文件

- `source_manifest.json`：源码来源与校验。
- `requirements-resolved.txt`：安装依赖冻结清单。
- `environment_check.json`：实际环境与导入结果；MPS 可见性为本次受限执行环境的检测结果。
- `offline_tests.json` 和三个 `.log`：31 项官方离线测试记录。
- `embedding_download.json`：模型版本、权重校验及真实编码输出。
- `local_retrieval_check.json`：纯本地检索实际结果。
- `local_model_download.json`：Qwen 提交、快照路径及权重校验值。
- `local_model_check.json`：本地接口真实调用与 token 用量。
- `local_run_summary.json`：HippoRAG2 与 dense 的实际样例结果及各自运行目录。
- `requirements-local-llm-resolved.txt`：MLX 本地推理环境冻结清单。
- `api_check.json`：DeepSeek 真实连接检查（不含密钥）。
- `model_comparison.md`、`model_comparison.json`：四组 50 题结果、缓存用量及配对比较。
- `deepseek_sample_hipporag_console.log`、`deepseek_sample_standard_console.log`：DeepSeek sample 运行日志。
- `dev50_deepseek_hipporag_console.log`、`dev50_deepseek_standard_console.log`：DeepSeek 开发集运行日志。

DeepSeek Flash 是提供方可更新的模型别名；后续实验应同时记录调用日期与返回的模型标识。缓存中的 token 元数据不能被当作实际账单。

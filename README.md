# HippoRAG 2 本地复现与 Idea 1 研究

最新结果（2026-10-17 汇总）：同一 50 题、227 文档开发集上的本地 Qwen 与 DeepSeek 四组对照已完成，见 `reports/model_comparison.md`。原始 Qwen 配置曾因抽取格式失败中止；本地成功结果来自明确记录的格式适配配置。

本项目使用 VS Code 和两个可选 LLM 后端：DeepSeek `deepseek-flash` API，或本地 MLX 上运行的 `Qwen2.5-1.5B-Instruct-4bit`。两者共用 Python 3.10 的 HippoRAG2 环境与本地 `BAAI/bge-small-en-v1.5` 向量模型。本地 MLX 推理另用 Python 3.12 环境 `.venv-local`。

**当前是替换模型后的功能基线，不是 ICML 2025 原论文分数复现。**本工作区没有复制旧项目的 `.env`；本地 Qwen 不需要密钥。旧的 DeepSeek 实验记录随项目迁移保留，但本轮工业诊断实验只调用本机 Qwen。实际已完成的验证看 `reports/STATUS.md`，不以这里列出的命令作为执行成功证据。

## 开始

在 VS Code 打开本文件所在目录。Python 解释器为 `.venv/bin/python`；已提供 `.vscode` 的任务和调试配置。此迁移后的工作区路径是 `/Users/mingyue/Documents/ChatGPT/hipporag-idea1`。

1. 在 VS Code 菜单 **Terminal → Run Task** 运行 `1. Check environment (offline)`。
2. 本地路径：先运行 `5. Start local Qwen server`，保持该任务运行；再运行 `6. Check local Qwen`、`7. Run local HippoRAG2 sample` 和 `8. Run local dense baseline sample`。服务器只绑定本机回环地址，按终端停止键可关闭。
3. API 路径：在本地 `.env` 填写 `DEEPSEEK_API_KEY`，再运行 `2. Check DeepSeek API`、`3. Run HippoRAG2 sample`、`4. Run dense baseline sample`。不要把密钥发到聊天或提交进 Git。

也可在项目终端执行通用离线检查：

```bash
.venv/bin/python scripts/check_environment.py
.venv/bin/python scripts/prepare_embedding.py
.venv/bin/python scripts/check_local_retrieval.py
.venv/bin/python scripts/run_offline_tests.py
```

本地 Qwen 路径：

```bash
.venv/bin/python scripts/prepare_local_model.py
.venv/bin/python scripts/start_local_server.py  # 在另一个终端保持运行
.venv/bin/python scripts/check_local_model.py
.venv/bin/python scripts/run_baseline.py --backend local --method hipporag --dataset sample
.venv/bin/python scripts/run_baseline.py --backend local --method standard --dataset sample
```

配置密钥后的 DeepSeek 路径：

```bash
.venv/bin/python scripts/check_environment.py --api
.venv/bin/python scripts/run_baseline.py --backend deepseek --method hipporag --dataset sample
.venv/bin/python scripts/run_baseline.py --backend deepseek --method standard --dataset sample
```

如果向量模型还没有成功下载，先运行 `prepare_embedding.py`；它需要访问 Hugging Face，成功后记录快照版本和权重 SHA256。

按 F5 可选择 API 或本地 Qwen 调试配置，从 `scripts/run_baseline.py` 进入官方源码设置断点。源码位于 `vendor/HippoRAG-main/src/hipporag/HippoRAG.py`。

本机已完成 HippoRAG2 环境、BGE 下载、31 项官方离线测试、本地 Qwen 与 DeepSeek 各自的 HippoRAG2/dense sample 和 50 题端到端对照。汇总见 `reports/STATUS.md`、`reports/model_comparison.md`；本地 sample 详见 `reports/local_run_summary.json`。

## 数据与范围

| 官方数据 | 问题数 | 检索文档数 |
|---|---:|---:|
| sample | 1 | 3 |
| musique | 1000 | 11656 |
| 2wikimultihopqa | 1000 | 6119 |
| hotpotqa | 1000 | 9811 |

这些是仓库内文件实际计数，未宣称等于完整原始数据集。sample 只有三个文档，Recall@5/200 很容易饱和，只用于流程检查，不能证明方法有效。本次 50 题开发集使用另行固定的 227 篇文档缩减语料。

后续正式子集实验示例：

```bash
.venv/bin/python scripts/run_baseline.py --method hipporag --dataset musique --limit 50 --allow-large-index
```

`--limit` 只限制问题数，**不会缩减检索语料**；这仍会为 11656 篇文档建立索引并产生 API 费用。不要误以为只处理 50 篇文档。当前没有启动完整语料规模的任务。

## 结果如何判断

- 输出在 `runs/<dataset>-<method>-<config-hash>/result.json`。
- 记录数据 SHA256、源码提交、模型设置、指标、检索段落、回答、时间和 QA 响应元数据。
- 检查抽取事实数、图节点/边、`queries_with_graph_seeds` 和 `run.log`。事实筛选失败可能回退到向量检索。
- `result.json` 的 `response_metadata` 记录 QA 返回；`cached_unique_response_usage` 汇总该运行目录中去重后的全部 LLM 缓存响应。四组开发集用量汇总见 `reports/model_comparison.md`。缓存汇总不等于 DeepSeek 实际账单。
- 重跑会复用缓存，重跑时间不能冒充冷启动耗时。
- 本地 BGE 是英语小模型，匹配官方英语数据；中文工业文档阶段需要另选中文/多语言向量模型并重新建索引。
- 上游 Transformers 向量后端在没有 CUDA 时使用 CPU；本地 Qwen 的 MLX 推理使用 Apple Metal，两者设备不同。
- 使用 DeepSeek 非思考模式保持抽取输出与成本较稳定；该提供方设置被明确记录，不改上游图算法。
- 本地 Qwen 采用 Hugging Face 固定提交快照；本地接口返回的 `default_model` 由启动脚本映射到该快照。两条后端各有独立缓存与运行目录，不能把两种 LLM 的指标直接归因于检索算法。

## 复现记录

- 官方源码：`vendor/HippoRAG-main/`，本地未修改；从 GitHub 官方压缩包下载。
- 固定提交与压缩包校验：`reports/source_manifest.json`。
- 2025 年论文时期参考提交：`242abfbefa03d6fce7a5c107e10ec24f22945b1f`，仅记录，不假定它就是论文实验使用的精确提交。
- Python 虚拟环境的底层运行时位于当前聊天工作目录的 `work/python/`。若移动项目或删除该目录，应重建虚拟环境。
- 若需要重新安装，在 Python 3.10 环境中安装 `requirements-local.txt`；本次环境的冻结清单（生成后）为 `reports/requirements-resolved.txt`。
- 本地 LLM 使用 Apple Silicon Metal 和 MLX LM；进入本项目时先启动 `.venv-local` 中的服务，权重保存在 `.cache/huggingface`。在无法访问 Metal GPU 的受限终端中启动会失败，应从本机 VS Code 任务启动。
- 本次 MLX LM 0.32.0 的完整依赖冻结清单在 `reports/requirements-local-llm-resolved.txt`；本地 Qwen 的固定模型提交、权重 SHA256 和真实接口检查分别在 `reports/local_model_download.json`、`reports/local_model_check.json`。

## 研究入口

阅读 `RESEARCH.md`：问题定义、代码改动候选点、公平对照、数据划分、否证条件。

2026-10-17 的前四项研究任务位于 `reports/idea1_literature_2026-10-17.md`（相关工作）、`reports/industrial_scenario_pf525.md`（工业场景）、`data/industrial_pf525/`（24 张证据卡和 36 个诊断案例）及 `reports/industrial_baseline_results.md`（四类预定对照与一个组合强基线）。从 VS Code 先运行 `5. Start local Qwen server`，再运行 `Industrial: local baselines`；结束后执行 `.venv/bin/python scripts/report_industrial_baselines.py`。此路径不会使用 DeepSeek API。

`data/idea1_synthetic_cases.json` 是虚构设备的五个任务设计样例，不是已收集的工业数据，也不是实验结果。

## 参考

- 论文：https://proceedings.mlr.press/v267/gutierrez25a.html
- 官方源码：https://github.com/OSU-NLP-Group/HippoRAG
- DeepSeek 接口：https://api-docs.deepseek.com/zh-cn/
- BGE 模型：https://huggingface.co/BAAI/bge-small-en-v1.5
- 本地 MLX LM：https://github.com/ml-explore/mlx-lm
- Qwen 权重：https://huggingface.co/mlx-community/Qwen2.5-1.5B-Instruct-4bit

## 固定 50 题开发集（2026-10-15）

`data/musique_dev50/manifest.json` 固定抽样种子、问题 ID、源文件及输出 SHA256。该集合由官方 MuSiQue 1000 题中抽取 50 题，保留全部支持段落并抽取每题 2 个原始干扰段落，合并为 227 篇文档。不同问题的文档共享一个检索语料库；不向模型提供支持标签。

这是缩减语料的开发诊断，不能与完整 11656 文档的官方实验分数比较。不要根据这一集合选择参数后再把它当独立测试集。

```bash
.venv/bin/python scripts/build_dev_subset.py
# 在另一终端先启动 scripts/start_local_server.py
.venv/bin/python scripts/run_baseline.py --backend local --dataset musique --dataset-dir data/musique_dev50 --method hipporag --per-query
.venv/bin/python scripts/run_baseline.py --backend local --dataset musique --dataset-dir data/musique_dev50 --method standard --per-query
.venv/bin/python scripts/report_dev50.py
```

VS Code 中也提供 `Dev50: local hipporag` 和 `Dev50: local standard` 两个任务。每题完成后更新运行目录中的 `result.json`，记录回答、指标和耗时。两条完整运行完成后，统计脚本生成 `reports/dev50_results.md` 与逐题 JSON。接口与模型固定快照、数据哈希、是否按题执行及问题限制均参与运行标识。

原 sample 的证据缺口和事实筛选问题见 `reports/sample_audit.md`。本次 DeepSeek 运行已在相同开发集上完成；使用 `--backend deepseek` 可复跑，并产生新的 API 用量。VS Code 提供 `Dev50: DeepSeek hipporag` 与 `Dev50: DeepSeek standard` 任务。

### 本轮发现的原始配置失败与显式适配

原始 Qwen 1.5B 配置在 227 篇文档中的 2 篇发生 NER JSON 解析失败，官方 OpenIE 停止整批建索引，未产生有效的 50 题 HippoRAG 分数。22 条 NER 响应达到长度上限，部分是重复实体。证据保存在 `reports/dev50_hipporag_console.log` 和 `reports/dev50_original_ner_failures.json`。

为继续诊断，增加显式 `--local-structured` 配置：两条方法均启用 repetition_penalty=1.1、repetition_context_size=256；仅抽取接口增加严格 JSON 提示、一次格式重试，以及嵌套字符串列表/裸三元组列表的结构规范化。不会补写字符串、丢弃失败文档或改变官方图算法。原始响应保留在缓存，重试/规范化另记 `extraction_attempts.jsonl`。这是适配后的功能基线，不能表述为原提示词配置原样成功。

```bash
.venv/bin/python scripts/check_local_adapter.py
.venv/bin/python scripts/run_baseline.py --backend local --dataset musique --dataset-dir data/musique_dev50 --method hipporag --per-query --local-structured
.venv/bin/python scripts/run_baseline.py --backend local --dataset musique --dataset-dir data/musique_dev50 --method standard --per-query --local-structured
.venv/bin/python scripts/report_dev50.py
```

统计脚本选择两条均已完成、数据/模型/适配配置一致的运行。VS Code 对应 `Dev50: adapted local hipporag` 与 `Dev50: adapted local standard`。不加适配参数的命令仍可用于复现原始失败。

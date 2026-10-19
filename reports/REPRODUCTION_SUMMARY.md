# HippoRAG2 已复现环境与基线总结

更新日期：2026-10-18（Asia/Shanghai）

当前项目：`/Users/mingyue/Documents/ChatGPT/hipporag-idea1`

## 1. 当前结论与复现范围

已在本地 Mac、VS Code 和 Python 虚拟环境中，使用官方 HippoRAG2 源码跑通建索引、向量编码、图检索和问答。保留 DeepSeek API 与本地 MLX Qwen 两个模型后端，向量编码均使用本地 BGE。

当前完成的是**替换模型与缩减语料条件下的功能复现和基线对照，不是 ICML 2025 原论文表格分数复现**。上游源码、模型快照、数据划分和运行结果均有记录。

| 内容 | 状态 | 证据与范围 |
|---|---|---|
| 本地环境与离线组件检查 | 已完成 | 既有记录为 31 项官方测试通过；测试使用模拟模型 |
| 官方 sample 端到端运行 | 已完成 | 1 题、3 文档；Qwen/DeepSeek × HippoRAG2/dense |
| 固定 MuSiQue 开发集 | 已完成 | 50 题、227 文档；两种模型各跑两种检索 |
| PowerFlex 525 工业诊断集 | 已完成 | 36 个构造案例、24 张证据卡；本地五组对照 |
| 原论文完整配置与完整语料评测 | 未完成 | 不将当前指标与原论文指标直接比较 |
| 原 Idea 1 方法 | 未实现 | 条件判断与澄清方向仅完成基线诊断 |
| 新方向：来源失效下的多跳证据韧性 | 未实现 | 已讨论研究问题与论文构思，尚无算法或实验结果 |

本次总结核对了环境版本和既有报告，没有重跑模型实验，也没有调用 DeepSeek API。本地服务最近一次成功检查记录是 2026-10-17；不据此声称服务当前仍在运行。

## 2. 环境配置

### 2.1 两套本地虚拟环境

| 用途 | 路径（相对项目根目录） | Python | 主要组件 |
|---|---|---|---|
| HippoRAG2、BGE、评测脚本 | `.venv/` | 3.10.22 | hipporag 2.0.0a5、torch 2.5.1、transformers 4.45.2、sentence-transformers 3.3.1、openai 3.29.0 |
| 本地 Qwen 推理服务 | `.venv-local/` | 3.12.14 | mlx 0.32.3、mlx-lm 0.32.0、transformers 5.19.0 |

两套环境在本机运行，不是云端或容器环境。VS Code 默认解释器为 `${workspaceFolder}/.venv/bin/python`。分开安装是为了隔离主项目与 MLX 推理的依赖版本。

- BGE 编码：当前上游 Transformers 后端在本机使用 CPU，向量为 384 维。
- Qwen 推理：通过 MLX 使用 Apple Silicon Metal；受限执行终端可能无法访问 Metal，已有成功实验通过本机 VS Code 任务启动。
- 本地服务地址：`http://127.0.0.1:8080/v1`，提供 OpenAI 兼容接口。
- `default_model` 是本地请求名称，由启动脚本映射到固定 Qwen 快照。
- 依赖冻结清单：`reports/requirements-resolved.txt` 与 `reports/requirements-local-llm-resolved.txt`。

### 2.2 工作区迁移与路径依赖

项目由旧目录 `/Users/mingyue/Documents/Codex/2026-10-14/za/outputs/idea1-study` 迁入当前工作区，保留了源码、运行结果、模型缓存和虚拟环境；**未复制旧 `.env`**。API 后端仍保留，若要在当前目录使用，需配置本地密钥；不要将密钥写入报告或版本库。

本次实际检查发现：

- `.venv/bin/python` 仍链接到 `/Users/mingyue/Documents/Codex/2026-10-14/za/work/python/cpython-3.10-macos-aarch64-none/bin/python3.10`。
- `.venv-local/bin/python` 仍链接到 `/Users/mingyue/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3`。

因此，复制项目目录不等于创建了完全独立、可搬移的环境。删除上述外部运行时会破坏对应虚拟环境；迁移到其他机器应重建环境。历史 JSON 中保留旧绝对路径属于原运行记录；当前模型快照路径以 `embedding_download.json` 和 `local_model_download.json` 为准。

## 3. 源码与模型固定信息

### 3.1 官方源码

- 论文：[From RAG to Memory: Non-Parametric Continual Learning for Large Language Models](https://proceedings.mlr.press/v267/gutierrez25a.html)，ICML 2025。
- 官方仓库：[OSU-NLP-Group/HippoRAG](https://github.com/OSU-NLP-Group/HippoRAG)。
- 本地源码：`vendor/HippoRAG-main/`。
- 固定提交：`d5c8329422e0a0b834a15874545cb6a74b4f9b26`。
- 固定压缩包 SHA256：`0aa7bad1b5753ce6991826ac91a6550aae66d2a5c0901679b5272c4742b82b2a`。
- 既有校验记录确认压缩包与本地上游源码一致，见 `reports/source_manifest.json`。项目自己的适配与运行脚本位于 `scripts/`。

该提交是已固定的官方实现，不等同于原论文实验使用的精确版本。

### 3.2 模型

| 模型用途 | 模型 | 固定信息 |
|---|---|---|
| 本地生成与抽取 | `mlx-community/Qwen2.5-1.5B-Instruct-4bit` | revision `8b403126fc14f14cfc99bb4cfa72ecbc129ea677` |
| 本地向量编码 | `BAAI/bge-small-en-v1.5` | revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` |
| API 生成与抽取 | `deepseek-flash` | 历史调用返回该标识；使用非思考配置；模型别名可随服务方更新 |

本地权重位于当前项目的 `.cache/huggingface/hub/` 下：

```text
models--mlx-community--Qwen2.5-1.5B-Instruct-4bit/snapshots/8b403126fc14f14cfc99bb4cfa72ecbc129ea677/
models--BAAI--bge-small-en-v1.5/snapshots/5c38ec7c405ec4b44b94cc5a9bb96e735b38267a/
```

权重 SHA256 与当前绝对路径分别记录在 `reports/local_model_download.json` 和 `reports/embedding_download.json`。BGE-small-en 为英语模型，当前实验主要使用英文数据，不能据此推断中文工业检索效果。

## 4. 实际运行流程与适配差异

### 4.1 HippoRAG2

离线：文档 → OpenIE 实体/三元组抽取 → 段落、实体与事实向量化 → 构建包含段落节点与实体关联的图 → 保存索引和模型响应缓存。

在线：问题 → 事实匹配 → LLM 事实筛选 → 图种子与段落信号 → Personalized PageRank → 排序段落 → 生成回答。

当事实筛选无有效结果时，可能回退到 dense 检索。因此需要同时检查图节点、抽取事实、graph seeds 与日志；仅有最终答案不能证明图检索发挥了作用。

### 4.2 Dense 基线

文档向量化 → 问题向量化 → 按向量相似度召回段落 → 使用相同后端模型生成回答。代码使用官方 `StandardRAG`，没有 OpenIE 图传播过程。

### 4.3 本地小模型适配

Qwen 原始配置在 227 文档开发集的 NER 阶段出现 2 篇解析失败，未完成原配置的 HippoRAG2 全流程。成功结果使用显式 `strict-json-v3` 适配：

- 抽取提示加入严格 JSON 要求；允许一次格式重试。
- 对可识别的嵌套字符串列表、裸三元组列表做结构规范化。
- 不补写事实、不丢弃失败文档、不修改官方 PPR 算法。
- 本地两种检索的相关生成设置均使用 `repetition_penalty=1.1`、`repetition_context_size=256`。
- 保留原响应与 `extraction_attempts.jsonl`，可审计重试和规范化。

DeepSeek 开发集使用原抽取提示词和非思考配置。跨后端差异同时包含模型与推理配置差异，不能全部归因于模型能力。工业实验另外使用动作 ID 分类提示，不是原论文的通用自由问答设置。

## 5. 已完成的基线结果

### 5.1 官方 sample：只验证流程

sample 包含 1 个问题和 3 篇文档。

| 后端与方法 | Recall@1 | 回答 EM | 回答 F1 |
|---|---:|---:|---:|
| 本地 Qwen + HippoRAG2 | 0% | 0% | 80% |
| 本地 Qwen + dense | 0% | 0% | 0% |
| DeepSeek + HippoRAG2 | 100% | 0% | 0% |
| DeepSeek + dense | 0% | 0% | 0% |

样例审查发现给定文档存在回答证据缺口。本地答案与 gold 的文字匹配不等于证据充分；不能用这一题比较方法优劣。详细记录见 `reports/sample_audit.md`、`reports/local_run_summary.json` 和 `reports/model_comparison.md`。

### 5.2 MuSiQue 固定开发集：50 题、227 文档

随机种子 `20261015`。从仓库数据抽取 50 题，保留全部支持段落并加入每题两个原始干扰段落，合并去重为 227 文档。数据与哈希位于 `data/musique_dev50/manifest.json`。这是缩减语料开发诊断，不是官方完整语料测试。

| 后端与方法 | Recall@1 | Recall@5 | Recall@10 | EM | F1 |
|---|---:|---:|---:|---:|---:|
| DeepSeek + HippoRAG2 | 37.17% | 86.17% | 96.83% | 52% | 61.05% |
| DeepSeek + dense | 37.50% | 80.00% | 86.50% | 50% | 63.52% |
| 本地 Qwen + HippoRAG2（适配后） | 31.17% | 81.17% | 90.00% | 6% | 14.08% |
| 本地 Qwen + dense（匹配生成设置） | 37.50% | 80.00% | 86.50% | 6% | 17.36% |

Recall@k 是既有评测器的支持文档召回指标，不等同于前 k 篇中找齐全部支持文档的问题占比；EM 为答案精确匹配，F1 为答案词级匹配。

结论：图检索在 Recall@5 上有提升，但当前两种后端都没有表现出回答 F1 优势。HippoRAG2−dense 的配对 F1 差，5000 次 bootstrap 的 95% 区间均跨越 0：本地 `[-0.1105, 0.0432]`，DeepSeek `[-0.1315, 0.0900]`。不能据此宣称图方法在回答质量上更优。

原始运行目录均位于 `runs/`：

| 组合 | 结果目录 |
|---|---|
| DeepSeek + HippoRAG2 | `musique-hipporag-4484a5d6cdac/` |
| DeepSeek + dense | `musique-standard-983e4dddd3dd/` |
| 本地 Qwen + HippoRAG2 | `musique-hipporag-919e8c07ccb6/` |
| 本地 Qwen + dense | `musique-standard-2fa2fe6c41f1/` |

每个目录的 `result.json` 保存指标与逐题信息。汇总见 `reports/model_comparison.md`、`reports/model_comparison.json`。

### 5.3 PowerFlex 525：本地工业诊断基线

依据厂商指南人工整理 24 张故障卡，构造 36 例：24 例已知故障码、12 例缺失故障码；开发集 24 例、测试分组 12 例。五种方法均使用本地 Qwen+BGE，每次最多提供 5 张卡，共完成 180 条结果；这轮没有使用 DeepSeek API。

| 方法 | 总决策正确率 | 已知码动作正确率 | 缺失码追问率 |
|---|---:|---:|---:|
| Dense | 22.2%（8/36） | 4.2% | 58.3% |
| HippoRAG2 | 47.2%（17/36） | 37.5% | 66.7% |
| Dense + metadata 硬过滤 | 77.8%（28/36） | 87.5% | 58.3% |
| Dense + 条件提示 | 69.4%（25/36） | 54.2% | 100% |
| Dense + 硬过滤 + 条件提示 | 97.2%（35/36） | 95.8% | 100% |

metadata 硬过滤使用人工整理的型号与故障码；条件提示要求判断适用性，缺码时追问。各方法在已知码案例上的证据@5 均为 100%，但回答质量明显不同。

HippoRAG2 实际抽取 82 个三元组，图含 128 个节点，36/36 次检索有图种子。组合基线唯一错误为动作 ID 拼写错误。当前小集已基本被简单组合解决，但尚未实现 Idea 1，不能说新方法已经胜出或已经被实验证伪。

该数据集来自同一手册与相近模板，既不是现场工单，也没有专家盲审；测试分组不代表跨手册泛化。数据：`data/industrial_pf525/`；原始结果：`runs/industrial_pf525_local/`；汇总：`reports/industrial_baseline_results.md`。

## 6. 复跑入口

以下命令均在当前项目根目录执行。优先使用本机 VS Code 终端。

### 6.1 启动并检查本地模型

```bash
# 终端 A：保持运行
.venv/bin/python scripts/start_local_server.py
```

```bash
# 终端 B
.venv/bin/python scripts/check_local_model.py
```

VS Code 对应任务：`5. Start local Qwen server`、`6. Check local Qwen`。

### 6.2 复跑本地 50 题对照

```bash
.venv/bin/python scripts/run_baseline.py --backend local --dataset musique --dataset-dir data/musique_dev50 --method hipporag --per-query --local-structured
.venv/bin/python scripts/run_baseline.py --backend local --dataset musique --dataset-dir data/musique_dev50 --method standard --per-query --local-structured
.venv/bin/python scripts/report_dev50.py
```

VS Code 对应任务：`Dev50: adapted local hipporag` 与 `Dev50: adapted local standard`。

### 6.3 复跑工业对照

```bash
.venv/bin/python scripts/run_industrial_baselines.py --phase all
.venv/bin/python scripts/report_industrial_baselines.py
```

VS Code 对应任务：`Industrial: local baselines`。可用 `--phase generation` 续跑动作分类阶段。该脚本限定本地回环接口。

### 6.4 API 后端保留情况

API 使用 `DEEPSEEK_API_KEY`、`DEEPSEEK_MODEL`、`DEEPSEEK_BASE_URL` 等本地配置，运行入口为 `scripts/run_baseline.py --backend deepseek`。当前整理任务未启动任何 API 调用。重新运行 API 基线会产生新的服务用量。

### 6.5 缓存与用量解释

已有完成记录、抽取缓存和向量索引可能被复用。再次执行不一定会重新生成所有回答；不要把续跑时间视为冷启动时间。改变配置时应使用独立运行记录，并保留旧结果用于比较。

`model_comparison.md` 中的缓存 token 总数是运行目录内去重响应库存，不是整个调试过程的实际账单；本地 token 不产生 DeepSeek 费用。工业结果中的 `generation_tokens` 仅统计最终动作分类调用，不含索引抽取和检索中的模型调用。

`--limit` 只限制问题数，不会自动缩减语料；要控制建索引规模，应使用已经固定的 `--dataset-dir data/musique_dev50`。

## 7. 可复用资产与未验证方向

可直接复用：官方检索实现、固定模型与语料、图索引和抽取缓存、逐题检查点、评测脚本、本地/API 双后端，以及 VS Code 任务配置。

尚未具备：来源依赖标签、有效推理链/AND–OR 证据结构、来源撤回压力测试、来源韧性指标、预算内主动补证算法及其强基线。这些属于后续研究工作，不应写入论文的“已完成贡献”。

当前基线适合做方法原型与小规模失效诊断。后续若要发表论文，还需独立测试划分、较完整语料、多个阅读模型、预算匹配的强基线、消融与统计检验，并区分检索错误、证据不足和模型使用证据失败。

## 8. 证据文件索引

以下路径均相对项目根目录；报告保留执行时状态，较早文件的时间与路径不一定等于当前状态。

| 文件 | 内容 |
|---|---|
| `reports/source_manifest.json` | 上游固定提交、压缩包校验 |
| `reports/environment_check.json` | 历史环境检查，不代表服务当前在线 |
| `reports/requirements-resolved.txt` | 主环境冻结依赖 |
| `reports/requirements-local-llm-resolved.txt` | MLX 环境冻结依赖 |
| `reports/embedding_download.json` | BGE 快照、权重校验、编码验证 |
| `reports/local_model_download.json` | Qwen 快照与权重校验 |
| `reports/local_model_check.json` | 最近保存的本地真实调用检查 |
| `reports/offline_tests.json` | 官方组件测试汇总 |
| `reports/sample_audit.md` | sample 证据缺口审查 |
| `reports/model_comparison.md` | 四组 MuSiQue 对照与统计解释 |
| `reports/dev50_analysis.md` | 本地小模型失败分析 |
| `reports/industrial_scenario_pf525.md` | 工业场景、来源和标注局限 |
| `reports/industrial_baseline_results.md` | 五组工业诊断结果 |
| `scripts/local_extraction_adapter.py` | 本地严格 JSON 抽取适配 |
| `.vscode/tasks.json` | VS Code 运行任务 |


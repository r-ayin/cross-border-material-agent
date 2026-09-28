# Cross-Border Material Generation Agent

## 数据与链路来源声明（2026-09-28 审计 A2-F1 后补充）
- data/Task_Data* 为赛事组织方公开分发数据集（task-meta.json 的 DataFileUrl 公开链接可下同一包）；部分商品 JSON 内含组织方签发的长效 OSS 预签名 URL（仅签名、不含 SecretKey），为保持数据集完整性不予改写；本仓 GitHub 镜像为 private。
- 生成链路凭证全部在仓库外（ds-test.env / ~/.dsh/credentials）；build/ 整体 gitignore；执行器 sha 锁定 631936…。

## 当前状态：2026-09-22 离线优化候选（不是最终参赛包）

工作台入口：`frontend/workbench.html`。静态证据：`frontend/assets/audit-report.json`、`preflight-plan.json`。

本轮修复图片六槽职责与拒绝门、视频真实时长和完整性、三语事实/尺码校验、策略证据记录、付费调用保护。新增 `--plan-only` 与 `--audit <目录>`。本地 156 项离线回归通过，完整 mock 流水线通过；mock 的结构完整不再等于发布合格。测试运行于 Python 3.14，已检查 Python 3.12 语法，尚未在比赛镜像执行真实模型链路。

默认不允许网络。设置 `AGENT_ALLOW_PAID_CALLS=1` 仅用于明确授权后的真实测试，**不能直接将此候选当作仅预置比赛三项环境变量的最终包提交**。正式比赛入口与白名单配置要在低价样片验证及用户授权后冻结。旧 `build/agent.zip` 尚未重新打包，不代表当前源码。

api.lk888.ai 已获样片测试授权，但当前被公司域名策略阻断；没有产生图片/视频生成请求。千问 Token Plan 未调用。第三方测试接口不进入比赛白名单运行路径。

历史素材保留原样：视频实测5.16秒、有可见水印；工艺/材质/生活场景图职责不足；韩文存在虚构尺码；旧策略虚构组件。67分是用户报告基线，没有官方分项回执，不能宣称本轮已提分。

本地复核：`python3 -m unittest discover -s tests -p 'test_*.py'`、`python3 tests/mock_e2e.py`、`python3 tests/build_offline_evidence.py`。预览：`python3 -m http.server 18765 --bind 127.0.0.1 --directory frontend`。

---

## 下文保留的历史说明（2026-08-28，不能当作当前能力证明）

> **一键出海：商品素材全自动生成** — 跨境电商 AI 素材生成 Agent
>
> ✅ **真实 API 端到端联调验证通过**（2026-08-28，实跑 product_8822221153828 粉色百褶半身裙）：
> - **11/11 产物全部真实生成，退出码 0，总耗时 510 秒**（限 30 分钟）
> - 文本：qwen3.8-max **SSE 流式**（解决思考模型长生成超时，三语言文案 1 分钟内并行完成）
> - 图像：qwen-image-3.0-pro 主图 + wan2.7-image-pro 详情图×5，同步 multimodal-generation 端点，6/6 成功，全部 1328×1328
> - 视频：happyhorse-1.1-t2v 异步任务链路打通，4.5MB mp4
> - 图生图：源商品图做参考输入验证可用（产品保真路径）
> - 风格路由：emotion=elegant/scene=commute → premium-editorial 风格族自动生效
> - 类目映射：LLM 精准命中 39153 女士半身裙，属性枚举值映射到目标平台属性体系
> 
> 基于纯 Python 3.12 标准库，无第三方依赖，离线可执行的跨境电商商品本地化素材生成 Agent。

---

## 项目概述

本 Agent 面向跨境电商（以 AliExpress 为示例）实现：

- **输入**：商品源数据 JSON（含标题/SKU/属性/源图）+ 平台类目库 + 属性库
- **输出**（11 个产物，严格命名、可解析）：
  - 商品文案 ×3（英文 / 韩文 / 葡萄牙文）
  - 主图 ×1（白底 ≥800×800）
  - 详情图 ×5（卖点图/工艺特写/材质特写/生活场景/全景展示）
  - 商品视频 ×1（i2v 产品展示视频，<200MB）
  - 策略说明文档 ×1

运行环境约束：
- 仅通过 DashScope 兼容 API 调用千问系列模型（qwen3.8-max/qwen-image-3.0-pro/wan2.7-image/wan2.7-i2v/qwen-vl-max 等）
- 无外部网络、无外部工具、无 MCP / Workflow / Embedding
- 单次运行 30 分钟 / 4GB 内存 / Python 3.12

---

## 架构设计

采用**纯代码阶段式 Pipeline + 线程池并发 + 指数退避重试 + 模型降级链**的轻量架构，排除所有重型编排框架（LangGraph/CrewAI/Temporal/Dify）。

### 五阶段流水线

```
P0 输入解析 (30s)  →  P1 类目属性映射 (2min)  →  P2 文案/图像/视频并行生成 (22min)  →  P3 策略文档 + 组装 (3min)  →  退出 0
```

| 阶段 | 任务 | 模型 | 并发 | 时间预算 |
|------|------|------|------|----------|
| P0 | 解析 --prompt、加载商品/类目/属性 | — | 1 | 30s |
| P0 | VL 理解源图（丰富生成 prompt） | qwen-vl-max | 1 | 60s |
| P1 | 选目标叶子类目（66 个属性叶子候选） | qwen3.7-max | 1 | 90s |
| P1 | 属性 / 销售属性枚举值映射 | qwen3.7-max | 1 | 90s |
| P2 | 三语言文案（en/ko/pt 并行） | qwen3.8-max→qwen3.7-max | 3 | 3min |
| P2 | 主图 1 + 详情图 5（并行） | qwen-image-3.0-pro→wan2.7-image-pro→wan2.7-image | 3 | 12min |
| P2 | 商品视频 1（i2v，源图做首帧） | wan2.7-i2v→happyhorse-1.1-r2v→happyhorse-1.1-t2v | 1 | 8min |
| P2 | OpenAI 兼容 /images/generations 兜底 | qwen-image-3.0-pro | — | 备用 |
| P3 | 策略文档 | qwen3.7-max | 1 | 2min |
| P3 | listing.json + 产物校验 + 退出码 | — | 1 | 30s |

### 容错三级机制

- **API 级**：指数退避重试（429 / 5xx / 网络异常，base=4s，max=60s，最多 4 次）
- **模型级**：每条路径内置 3-4 层降级链
- **阶段级**：Budget 守卫，剩余时间不足时主动降级/跳过

### 合规保障

- **图像**：所有 prompt 含 IMAGE_NEGATIVE_PROMPT（no text, no watermark, no logo, no border, no collage…），防止 40% 生成图含乱码文字
- **主图**：强制纯白底 RGB(255,255,255)，产品占画面 70%
- **详情图**：5 张商业化编排（卖点组合 / 工艺特写 / 材质特写 / 生活场景 / 全景展示）
- **文案**：系统提示词严禁医疗声明、夸大用语、侵权品牌、伪造认证
- **类目属性映射**：源数据没有的属性绝不虚构（宁可留空）
- **尺码表**：三语言文案强制 cm + inch 双单位
- **格式自适应**：图像产物按魔法字节检测真实格式（png/jpeg），自动匹配扩展名

---

## 文件结构

```
cross-border-material-agent/
├── agent/                    # 提交包（ZIP 打包的根目录）
│   ├── agent.py              # 入口：--prompt / --version
│   ├── agent.json            # {"runtime":"python","version":"1.0.0"}
│   ├── requirements.txt      # 纯标准库，无第三方依赖
│   └── src/
│       ├── agent.py          # (顶层入口)
│       ├── budget.py         # 时间预算守卫 + 结构化日志
│       ├── dsapi.py          # DashScope API 客户端（Chat / Async Task / OpenAI 图像 / 重试 / 下载）
│       ├── input_parse.py    # --prompt 路径解析 + 商品 / 类目 / 属性加载
│       ├── category_map.py   # 叶子类目选择 + 属性映射（66 个属性叶子候选）
│       ├── prompts.py        # 文案 / 图像 / 策略提示词模板
│       ├── copy_gen.py       # 三语言文案并行生成
│       ├── image_gen.py      # 主图 + 5 详情图（含格式自适应 + OpenAI 兜底）
│       ├── video_gen.py      # 商品视频（i2v 链）
│       ├── strategy.py       # 策略文档
│       └── assemble.py       # 产物校验 + listing.json
├── tests/
│   └── mock_e2e.py           # 端到端 mock 测试（桩掉 API，验证编排）
├── research/                 # 调研产出（4 份报告）
│   ├── oss-projects.md       # 开源项目盘点
│   ├── architecture-survey.md# 成熟架构 + 理想架构设计
│   ├── localization.md       # 三市场本地化策略（尺码换算 / 文化禁忌）
│   └── best-practices.md     # 最佳实践 + AliExpress 合规规则
├── data/
│   └── Task_Data.zip         # 示例数据
└── build/
    └── agent.zip             # 打包产物（24.6 KB）
```

---

## 运行与打包

### 1. 环境准备

- 在 [www.qianwenai.com](https://www.qianwenai.com) 注册并完成实名认证
- 在 [platform.qianwenai.com](https://platform.qianwenai.com) 获取 API Key
- 熟悉 API 调用：https://platform.qianwenai.com/docs/developer-guides/getting-started/first-api-call

### 2. 本地测试（mock 模式，无需 API Key）

```bash
cd cross-border-material-agent
python3 tests/mock_e2e.py
# 期望输出：MOCK E2E TEST PASSED（11/11 artifacts OK）
```

### 3. 本地实跑（需要 DASHSCOPE_API_KEY）

```bash
export DASHSCOPE_API_KEY="<your-dashscope-key>"
export DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/api/v1
export OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

cd agent
python3 agent.py --version                    # 1.0.0
python3 agent.py --prompt "读取 /path/to/input/ 目录下目标商品的全部信息文件，\
    提取指定内容，按规范生成输出文件并保存至 /path/to/output/。"
```

### 4. 打包产物

```bash
# agent.zip 已在 build/ 目录下生成
ls -la build/agent.zip
```

---

## 质量维度对齐

| 维度 | 权重 | Agent 应对策略 |
|------|------|----------------|
| A1 内容合规 | 25% | COPY_SYSTEM 禁用医疗/夸大/品牌/伪造认证；IMAGE_NEGATIVE_PROMPT 去文字水印 |
| A2 素材规格 | 20% | 主图 1328×1328 ≥ 800×800；详情图 1328×1328 > 260px；视频 < 200MB；文件按魔法字节命名 |
| A3 类目属性 | 18% | 66 个属性叶子类目候选 + LLM 映射；属性枚举值严格匹配 |
| A4 本地化 | 15% | 三市场差异化 MARKET_GUIDANCE；尺码表 cm+inch 双单位；文化禁忌写入提示词 |
| A5 事实一致 | 10% | 文案模板强制 Source Information 段（平台名 + 商品 ID + URL）；属性映射不虚构 |
| A6 出图可用率 | 7% | 主图 / 详情图多模型降级链；OpenAI 兼容 endpoint 兜底；negative_prompt 减少瑕疵 |
| A7 出视频可用 | 5% | wan2.7-i2v（源图首帧）→ happyhorse-r2v → happyhorse-t2v 三级降级 |

---

## 关键设计决策

1. **纯标准库零依赖**：运行时环境无网络安装能力，任何第三方 wheel 都需要精确匹配 Debian 12 x86_64 + Python 3.12 平台标签，打包复杂度高。纯标准库 ZIP 仅 24KB，零风险。

2. **阶段式 Pipeline 而非 Agent 框架**：本任务是确定性批处理（输入→固定产物集合），LangGraph/CrewAI 等 Agent 框架的自主规划能力在此场景下是过度设计，反而消耗额外 token 和时间。

3. **多端点探测 + OpenAI 兼容兜底**：无法预先确知新模型（qwen-image-3.0-pro / wan2.7-*）的确切 endpoint 和入参格式。内置 `/services/aigc/text2image/image-synthesis` + `/services/aigc/multimodal-generation/generation` + `/images/generations` 三条路径探测，任一成功即返回。

4. **源图做视频首帧**：任务允许「正确识别赛题数据中提供的 URL 作为输入」，直接用源商品图作为 wan2.7-i2v 首帧，避免依赖生成图像带来的二次不一致。

5. **格式自适应**：不同模型返回 png/jpeg 不定，下载后读魔法字节再决定扩展名，避免扩展名与内容不符导致平台解析失败。

---

## 调研产出（research/）

- **oss-projects.md** — 20 个相关开源项目盘点，Top3：MoneyPrinterAICreate（⭐323，原生 Wan2.1）、DiffSynth-Studio（⭐13K，统一 Diffusion 推理引擎）、ComfyUI-MultiModal-Prompt-Nodes（Qwen VL + Wan 多模态 prompt）
- **architecture-survey.md** — LangGraph/CrewAI/Dify/AutoGen/Prefect/Temporal 对比 + 本任务理想架构设计（五阶段流水线 + 并发 + 容错 + 时间预算表）
- **localization.md** — 三市场文案风格 / 尺码换算表（women_tops/men_tops/bottoms_waist/shoes × CN/US/EU/KR/BR）/ 文化禁忌速查
- **best-practices.md** — 30 条来源的 AE 上架规则汇总：主图白底 RGB(255,255,255) / 5 图商业化编排 / 30s 视频分镜 / 文案红线 / 尺码表双单位

---

## 许可

本仓库代码使用 MIT 许可。
调研产出基于公开网络资料综合整理。

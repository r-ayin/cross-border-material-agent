<div align="center">

[![version](https://img.shields.io/badge/version-1.1.0-2F6FEB?style=flat-square)](agent/agent.json)
[![python](https://img.shields.io/badge/python-3.12%2B-2F6FEB?style=flat-square)](https://www.python.org/)
[![dependencies](https://img.shields.io/badge/dependencies-zero-1A7F5A?style=flat-square)](agent/requirements.txt)
[![tests](https://img.shields.io/badge/tests-183%20offline-1A7F5A?style=flat-square)](tests/)
[![markets](https://img.shields.io/badge/markets-US%20%7C%20KR%20%7C%20BR-2F6FEB?style=flat-square)](research/localization.md)
[![license](https://img.shields.io/badge/license-MIT-1A7F5A?style=flat-square)](#-许可)

</div>

---

# 跨境商品素材生成 Agent

**一件商品源数据 → 11 件可直接上架的多语言素材。离线可预演，生成需授权。**

`一件商品，一条命令，一次运行` —— 面向跨境电商（AliExpress 等）的素材本地化生成 Agent。
读取商品源数据 JSON 与平台类目库，输出三语文案、六张商品图、一支商品视频与一份投放策略文档，
全部产物命名严格、体积受控、可被平台解析。

[English](README.en.md) · [产品说明](docs/problem-detail.html) · [流水线 SOP](docs/pipeline-sop.md) · [调研报告](research/)

---

## 📖 目录

| | |
|---|---|
| [🎯 核心能力](#-核心能力) | [📦 产物清单](#-产物清单) |
| [⚡ 快速开始](#-快速开始) | [🔧 配置](#-配置) |
| [🧭 命令行](#-命令行) | [🏗 流水线架构](#-流水线架构) |
| [🛡 质量门](#-质量门) | [📸 图像生成](#-图像生成) |
| [🎬 视频生成](#-视频生成) | [✍️ 文案生成](#-文案生成) |
| [🗂 类目与属性映射](#-类目与属性映射) | [🖥 素材工作台](#-素材工作台) |
| [📁 项目结构](#-项目结构) | [🧪 测试](#-测试) |
| [📄 许可](#-许可) | |

---

## 🎯 核心能力

### 两段式运行：先离线规划，再授权生成

Agent 的默认状态是**禁网**。传入 `--plan-only`，它只读源数据、推导完整创意方案、写出生成计划，
**零模型调用、零网络请求**，几秒内产出可评审的 `generation_plan.json`——分镜、字幕、帧分配、
六个图像槽位的角色契约，全部先落到纸面。

只有当你显式设置 `AGENT_ALLOW_PAID_CALLS=1` 时才会真正调用模型。
配上 API Key 不等于授权：写入密钥只是配置，授权是一个独立的开关。

### 事实优先于修辞

素材生成 Agent 最常见的失败不是出不来图，而是出**好看但错**的图——虚构的面料成分、
凭空的认证、算错的尺码。本 Agent 把"不许编"写进了代码而不只是提示词：

- **属性不虚构**：类目与属性的每个取值都强制取自平台库，`attrId` 不在库中直接丢弃，
  `valueId` 不在枚举中直接丢弃；仅当该属性在库中根本没有枚举定义时才接受自由文本。
- **尺码不换算**：没有实测数据就标注缺失，**绝不**做厘米/英寸或国际码的推算——
  任何形式的等码换算都会被质量检查拦下。
- **红线词需举证**：成分、洗护、物流、认证、性能、季节、货币这 7 类词，
  除非在源数据中找到逐字证据，否则一律判为未验证。
- **材质词需举证**：13 种材质表述同理，源证据带否定含义（"无""不含""not"）时反向降级。

### 结构性验收，而非"跑完就算"

生成完成不等于可用。Agent 对 11 件产物逐件做本地结构校验，并给出**三级结论**与对应退出码，
让 CI 或流水线能够据此自动放行或拦截。

### 零依赖

纯 Python 标准库实现（`urllib` / `json` / `concurrent.futures` / `threading` / `struct`），
`requirements.txt` 里只有两行注释。无需 `pip install`，在无外网、无编译器的受限沙箱里
直接解压即跑。5049 行源码，不引入 LangGraph / CrewAI / Dify 等编排框架——
这个任务是确定性批处理，自主规划能力在此是过度设计。

---

## 📦 产物清单

一次运行产出 **11 件必需产物**，文件名严格固定，可被下游脚本直接解析：

| 类别 | 产物 | 规格 |
|:---:|---|---|
| 文案 | `product_description_en.md` | 英文（US）· 六章节 · 5–7 条卖点 |
| 文案 | `product_description_ko.md` | 韩文（KR）· 本地化章节标题 |
| 文案 | `product_description_pt.md` | 巴西葡语（BR） |
| 图像 | `main_image.png` | 1328×1328 · 纯白底 · 产品占幅 ≥70% |
| 图像 | `detail_image_1.png` | 整体卖点 |
| 图像 | `detail_image_2.png` | 工艺特写 |
| 图像 | `detail_image_3.png` | 材质特写 |
| 图像 | `detail_image_4.png` | 生活场景 |
| 图像 | `detail_image_5.png` | 全貌展示 |
| 视频 | `product_video.mp4` | 1280×720 · 5s · < 200 MB |
| 文档 | `strategy_document.md` | 投放与内容策略说明 |

**附带产物**

| 文件 | 说明 |
|---|---|
| `listing.json` | 结构化 listing，资产以数组形式索引 |
| `quality_report.json` | 逐产物技术有效性与验收状态 |
| `run_manifest.json` | 阶段事件时间线 + 请求计数快照 |
| `generation_plan.json` | `--plan-only` 产出的离线生成计划 |
| `copy_quality.json` | 文案事实与语言质量审计结果 |
| `video_manifest.json` / `product_video_srt.srt` | 视频生成元数据与外挂字幕 |

---

## ⚡ 快速开始

### 前置条件

```
Python 3.12+ · 无需安装任何依赖 · 运行期需要千问平台 API Key（真实生成时）
```

在 [千问平台](https://platform.qianwenai.com) 取得 API Key。

### 1 · 离线预演（无需 Key，不联网）

先看看它打算怎么做：

```bash
cd agent
python3 agent.py --plan-only --prompt "读取 /path/to/input/ 目录下目标商品的全部信息文件，提取指定内容，按规范生成输出文件并保存至 /path/to/output/。"
```

输出：

```
offline plan: 11 required slots; model calls=0
```

以及一份完整的 `generation_plan.json`。这一步**不消耗任何额度**，适合放进评审和回归流程。

### 2 · 本地全链路演练（无需 Key，桩掉全部网络）

```bash
python3 tests/mock_e2e.py
```

`mock_e2e.py` 会把 `socket` / `urlopen` 全部换成抛错的桩，
断言"任何真实网络调用都会让测试失败"。它验证编排、结构完整性与退出码语义，
**并且刻意断言 mock 结果不等于发布合格**（结构完整时退出码必须是 `2`，不是 `0`）。

### 3 · 真实生成（需 Key + 显式授权）

```bash
export DASHSCOPE_API_KEY="<your-key>"
export DASHSCOPE_BASE_URL="https://dashscope.aliyuncs.com/api/v1"
export OPENAI_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export AGENT_ALLOW_PAID_CALLS=1          # ← 授权开关，独立于 API Key

cd agent
python3 agent.py --version               # 1.1.0
python3 agent.py --prompt "读取 /path/to/input/ ... 保存至 /path/to/output/。"
```

> 运行前请确保输出目录为空。检测到上一轮的残留产物时，Agent 会直接拒绝启动，
> 以免旧文件被误判为本轮的成功结果。

### 4 · 打开素材工作台

```bash
python3 -m http.server 18765 --bind 127.0.0.1 --directory frontend
# 浏览器打开 http://127.0.0.1:18765/workbench.html
```

需要视频可拖动进度条时，用带 Range 支持的预览服务器：

```bash
python3 tools/preview_server.py          # 默认 18766，支持 Range 请求
```

---

## 🔧 配置

| 环境变量 | 必需 | 说明 |
|:---|:---:|---|
| `DASHSCOPE_API_KEY` | 真实生成时 | 千问平台 API Key |
| `DASHSCOPE_BASE_URL` | 真实生成时 | DashScope 异步任务端点 |
| `OPENAI_BASE_URL` | 真实生成时 | OpenAI 兼容端点（Chat / Image） |
| `AGENT_ALLOW_PAID_CALLS` | 真实生成时 | 授权开关，必须为 `1`，否则所有网络请求被拒 |

运行时限制（在 `RuntimePolicy` 中强制执行）：

| 约束 | 值 |
|---|---|
| 单次请求上限 | 64 |
| 单次媒体请求上限 | 24 |
| 硬截止时间 | 28 分钟（预算末端 45s 起） |
| 网络出口 | 仅 HTTPS，且不接受内嵌凭证的 URL |
| 脱敏 | 令牌、`api_key`/`authorization` 值、URL 查询串一律替换后再进日志与产物 |

---

## 🧭 命令行

```
python3 agent.py [--prompt TEXT] [--version] [--plan-only]
                 [--audit OUTPUT_DIR] [--check-plan JSON_FILE]
```

| 参数 | 说明 |
|---|---|
| `--prompt TEXT` | 自然语言指令，Agent 从中解析输入目录与输出目录 |
| `--version` | 打印版本号（`1.1.0`）后退出 |
| `--plan-only` | **只规划不生成**。不读取密钥、不发网络请求，写出 `generation_plan.json` |
| `--audit OUTPUT_DIR` | **只读检查**已有产物目录，结果以 JSON 打到 stdout，不执行任何生成 |
| `--check-plan JSON_FILE` | 校验从浏览器导出的计划文件，**永不执行其中内容** |

### 退出码

| 码 | 含义 |
|:---:|---|
| `0` | 全部 11 件产物验收通过（`publish_ready`） |
| `2` | 结构完整，但仍需人工复核 |
| `1` | 未达结构完整 |
| `124` | 触发硬截止时间，进程被看门狗终止 |

> `2` 是一等公民，不是失败。结构完整与发布合格是两件事，
> Agent 不允许把前者伪装成后者。

---

## 🏗 流水线架构

**阶段式 Pipeline + 线程池并发 + 指数退避重试 + 模型降级链**。
四个阶段，媒体生成三路并行，`ThreadPoolExecutor(max_workers=3)`。

```
P0  输入解析 ──────────▶ 视觉观察 ──┐
                                    │
P1  类目 + 属性映射 ─────────────────┤
                                    ▼
P2  文案 ∥ 图像 ∥ 视频   （三线程并发）
                                    │
P3  格式校正 → 策略文档 → listing.json → 质量报告 → 退出码
```

| 阶段 | 任务 | 模型 |
|---|---|---|
| P0 | 解析 `--prompt`，加载商品 / 类目 / 属性 | — |
| P0 | 视觉观察源图（仅描述可见几何、颜色、图案） | `qwen-vl-max` |
| P1 | 选目标叶子类目（66 个带属性定义的候选） | `qwen3.7-max` |
| P1 | 属性 / 销售属性枚举值映射（三级策略） | `qwen3.7-max` |
| P2 | 三语文案（en / ko / pt 并行） | `qwen3.8-max` → `qwen3.7-max` |
| P2 | 主图 ×1 + 详情图 ×5（6 槽位并行） | 见[图像生成](#-图像生成) |
| P2 | 商品视频 ×1（源图作首帧） | `wan2.7-i2v-2026-04-25` → `happyhorse-1.1-r2v` → `happyhorse-1.1-t2v` |
| P3 | 策略文档 | `qwen3.7-max` |
| P3 | 格式自适应 → `listing.json` → 质量报告 | — |

### 三级容错

| 层级 | 机制 |
|---|---|
| **API 级** | 指数退避重试（429 / 5xx / 网络异常）。基础 4s → 上限 60s，最多 4 次，带 0–2s 抖动。Chat 通道更宽：6 次 / 上限 90s |
| **模型级** | 每条生成路径内置降级链，失败时**推进到下一个模型**而非重复同一次调用 |
| **阶段级** | `Budget` 守卫 + `HardDeadline` 看门狗。剩余时间不足时主动降级；供应商持续滴字节绕过协作式 HTTP 超时时，看门狗在 28 分钟强杀本进程 |

### 凭据纪律

`PolicyError` 在 `with_retry` 中**不可重试**——授权失败是策略信号，不是瞬时故障，
重试只会重复拒绝对同一个目标的访问。

---

## 🛡 质量门

### 三级结论

| 判定 | 含义 |
|---|---|
| `technical_valid` | 该产物通过本地结构检查（尺寸、体积、章节、非空、容器完整性） |
| `structurally_complete` | 11 件产物**全部** `technical_valid` |
| `publish_ready` | 11 件产物**全部** `accepted`，即技术与内容双重通过 |

### 结构检查项

| 产物 | 检查 |
|---|---|
| 文案 / 策略 | 体积 0–1 MB · 无空字节 · 六章节齐全且标题本地化 · 标题 ≤128 字符 |
| 图像 | ≤5 MB · 格式合法 · 主图最小边 ≥800 · 详情图最小边 ≥261 |
| 视频 | 交给 `media_probe` 深度校验 |

### `media_probe` —— 不解码的 MP4 校验器

纯标准库解析 ISO BMFF 盒子结构，**从头到尾不解码视频帧**，
因此可以在受限环境里对一个大文件做有界检查：

- 顶层 `ftyp` / `moov` / 非空 `mdat` 齐备
- 拒绝分片 MP4（`moof` / `mvex`）与多视频轨 → 状态 `unsupported` 而非 `invalid`
- 轨道数 1–128
- 逐样本表一致性：`stsd` / `stts` / `stsz` / `stsc` / `stco`–`co64` 全表边界与顺序
- `ctts` / `stts` 合成覆盖 + `elst` 编辑列表（rate-1，最多 2 条，允许前导空 edit）
- **时长取视频合成覆盖 ∩ 编辑列表**，不是音轨时长也不是容器时长——
  音频轨长不会灌水视频时长
- 输出 `video_start_seconds`，定位前导空 edit 之后的真实内容起点
- 检查期间文件被改动 → 直接判 `invalid`
- 有界防护：`20000` 个盒子 / `1000000` 条表项上限，防止畸形文件打爆内存

---

## 📸 图像生成

### 六个槽位，六种职责

六个槽位各自绑定明确的角色契约，**不允许串味**——
一张图不能同时想当卖点图和工艺图：

| 槽位 | 角色 | 硬性要求 |
|---|---|---|
| `main_image` | `overall_product` | 单件完整商品 · 纯白底 RGB(255,255,255) · 方形构图 |
| `detail_image_1` | `overall_selling_point` | 突出源图中可见的设计特征 |
| `detail_image_2` | `craftsmanship` | 可见缝线 / 边缘 / 做工特写，细节占画面 60–80% |
| `detail_image_3` | `material_appearance` | 表面质感与垂坠特写，占画面 70–85% |
| `detail_image_4` | `lifestyle` | 真实室内外日常场景，**非**白底抠图 |
| `detail_image_5` | `complete_overview` | 完整未裁切全貌，**禁止**拼图与虚构背面 |

### 模型链

| 目标 | 降级链 |
|---|---|
| 主图 | `qwen-image-3.0-pro` → `wan2.7-image-pro` → `wan2.7-image` |
| 详情图 | `wan2.7-image-pro` → `wan2.7-image` → `qwen-image-3.0-pro` |

每槽位最多 3 次候选，每次失败推进模型。端点按
`multimodal-generation` → `text2image/image-synthesis` 顺序探测，
仅在 `400/404/405/422` 时换端点——任务已受理的错误直接抛出，不做无谓重投。

### 白底校验

白底是**测量**出来的，不是**相信**出来的：
`WHITE_BG_NEAR = 245`，白像素占比需 ≥ `0.9`，采样带取图像边缘 5%。
深色背景的"白底图"不会被放行。JPEG 无 alpha 通道，
其白底状态恒为 `unknown`，落入 `.needs_review` 后缀而不是正式文件名。

### 审美 critic

`aesthetic_critic` 用视觉模型对每个候选做四维打分
（背景洁净度 / 产品保真度 / 审美吸引力 / 无瑕疵），总分 0–10。
它**只比对源参考图，不读生成图**——评审的是"像不像源商品"，不是"好不好看"。

拒绝门：

| 条件 | 判定 |
|---|---|
| 总分 `< 26` | 重试 |
| 任一维度 `< 5` | 重试 |
| 角色匹配为否 | 重试 |
| 无参考图 | 强制降级为 `unknown` |

任一项 `failed` → 该候选 `rejected`；存在 `unknown` → 落盘为 `.needs_review` 后缀，
**绝不冒充正式产物**。

---

## 🎬 视频生成

### 本地选型，不做失败重投

视频链路与图像链路的关键区别：**模型在提交前本地选定，失败即停，绝不重投**。
重复提交同一段视频既烧额度又可能双倍计费。

```
wan2.7-i2v-2026-04-25  （图生视频，源商品图作首帧）
        ↓ 能力不匹配
happyhorse-1.1-r2v     （参考图驱动）
        ↓ 能力不匹配
happyhorse-1.1-t2v     （文生视频，需显式 allow_unreferenced_video=True）
```

每轮只允许 **1 次**生成 POST（`submission_count_limit: 1`）。

### 五镜分镜

`hook → problem → product → proof → CTA`，30s 与 15s 两套时间边界。
预算不足 300s 时自动降级到 15s 方案。

| 方案 | 镜位边界（秒） |
|---|---|
| 30s | `0 · 3 · 8 · 20 · 25 · 30` |
| 15s | `0 · 2 · 4 · 10 · 13 · 15` |

`creative_plan` 进一步把分镜编译成帧级精确的 EDL（30s = 720 帧），
并对字幕轨做留白处理，保证字幕不会压住关键画面。

### Motion prompt 纪律

每一拍的提示词都强制三件事：**参考图权威**（不得转向看不见的面）、
**禁止添加文字 / 水印 / 价格图形**、**只用轻微运镜**。

### 字幕

字幕只作为外挂 sidecar，**永不烧录**进画面。
只接受实测时间线验证过的 cue，最多 10 条。
BGM 仅保留常量声明，状态恒为 `not_generated`——不假装生成了音乐。

---

## ✍️ 文案生成

三种语言，各自有本地化章节标题：**英文（US）/ 韩文（KR）/ 巴西葡语（BR）**。
英文标题**不算**满足韩文章节要求。

### 固定六章节

`Key Features` → `Product Information` → `Size Chart` → `Source Information` → `Image Guide` → `Video`

### Schema

| 字段 | 约束 |
|---|---|
| `title` | ≤128 字符 |
| `bullets` | 5–7 条，每条 ≤60 字符，不得重复 |
| `keywords` | 8–12 条，不得重复 |
| 结构 | 4 字段齐全，拒绝重复键 / NaN / 内嵌对象 |

### 事实审计

| 检查 | 触发标记 |
|---|---|
| 来源 platform / offer_id / URL 未精确出现在 Source Information | 事实不符 |
| 源 SKU JSON 块未逐字节等价 | 引用数据存疑 |
| 出现源数据以外的 URL | 未知 URL |
| 文中任何数字不在源证据或源尺码标签中 | 数字无据 |
| 命中 7 类红线词且非源证据逐字 | 未验证声明 |
| 13 种材质词缺源证据 / 证据含否定含义 | 材质待核 |
| 出现国际等码换算 | 尺码换算待核 |
| 中文残留 / 三语之间混排 | 语言不纯 |

任一 `facts:` / `language:` 问题触发源模板兜底重写。
即便机械检查全部通过，状态仍恒为 `needs_review`——
**机器能验的只有事实，语言母语感与语义合理性必须人来判断。**

---

## 🗂 类目与属性映射

| 数据源 | 规模 | 用途 |
|---|---|---|
| `clothing_attributes.json` | **66** 个带属性定义的叶子类目 | 语义映射候选集 |
| `clothing_categories.json` | **3546** 个叶子类目 | 类目树遍历 |

### 属性映射三级策略

按成本从低到高依次尝试，能确定性解决的绝不调用模型：

```
1. 确定性别名匹配（零模型调用）
   中文别名精确 / 包含匹配
        ↓ 未命中
2. 批量 LLM 映射（一次调用处理全部属性）
        ↓ 未命中
3. 逐项 LLM 映射（旧版兜底）
```

确定性结果在 `attrId` 冲突时优先。

### 不虚构的强制点

- 类目返回值强制取自库中；找不到对应叶子直接抛错，绝不近似匹配
- `attrId` 不在库中 → 丢弃；`valueId` 不在枚举中 → 丢弃
- 销售属性值必须命中枚举白名单，否则整条放弃
- 仅当属性在库中完全没有枚举定义（`customized`）时才接受自由文本
- 品牌与认证本就不在库中，因此**结构上**无法被"映射"出来

---

## 🖥 素材工作台

`frontend/workbench.html` 是一个零依赖的单文件工作台，用于评审与演示：

- 商品选择器 · 素材灯箱大图 · 缩略图条
- 三语文案内置渲染，>1 MB 拒收
- 语言筛选（全部 / EN / KO / PT）与素材类型筛选（图片 / 视频 / 文案）
- 单件下载 · 全文复制
- hash 路由（`#cover` / `#work` / `#work/video`），支持前进后退

预览服务器：

```bash
python3 -m http.server 18765 --bind 127.0.0.1 --directory frontend
python3 tools/preview_server.py --port 18766    # 带 Range，视频可拖动
```

---

## 📁 项目结构

```
cross-border-material-agent/
├── agent/                      # 提交包根目录
│   ├── agent.py                # 入口：--prompt / --version / --plan-only / --audit
│   ├── agent.json              # {"runtime":"python","version":"1.1.0"}
│   ├── requirements.txt        # 纯标准库，零第三方依赖
│   └── src/
│       ├── runtime_policy.py   # 授权、请求预算、硬截止、凭据脱敏
│       ├── input_parse.py      # --prompt 解析 + 商品/类目/属性加载
│       ├── creative_plan.py    # 离线创意编译器（分镜/EDL/字幕/事实台账）
│       ├── planning.py         # 离线计划打包 + 外部计划校验
│       ├── style_router.py     # 商品信号分析 + 跨市场风格画像
│       ├── category_map.py     # 叶子类目选择 + 三级属性映射
│       ├── copy_gen.py         # 三语文案生成 + 事实审计
│       ├── image_gen.py        # 六槽位图像生成 + 白底/格式校验
│       ├── aesthetic_critic.py # 四维视觉评审 + 拒绝门
│       ├── video_gen.py        # 视频生成 + 分镜 + 字幕
│       ├── media_probe.py      # 纯标准库 MP4 结构校验
│       ├── strategy.py         # 策略文档
│       ├── prompts.py          # 提示词模板
│       ├── dsapi.py            # DashScope / OpenAI 兼容客户端
│       ├── budget.py           # 时间预算守卫 + 结构化日志
│       └── assemble.py         # 产物校验 + listing.json + 质量报告
├── tests/                      # 183 项离线回归
├── frontend/                   # 素材工作台
├── tools/                      # 成片精修、带 Range 的预览服务器
├── scripts/                    # 成片构建、供应商 runner、部署服务
├── docs/                       # SOP、提示词规格、赛题说明
├── research/                   # 20 篇调研报告
├── audit/                      # 对抗审计发现与处置
└── deploy/                     # systemd unit + HTTPS 代理
```

---

## 🧪 测试

```bash
python3 -m unittest discover -s tests -p 'test_*.py'   # 183 项，16s
python3 tests/mock_e2e.py                               # 全链路密闭演练
python3 tests/build_offline_evidence.py                 # 重建离线证据
```

| 测试文件 | 覆盖 |
|---|---|
| `test_copy_quality.py` | 文案 schema、事实一致性、三语纯净度、预算耗尽不调模型 |
| `test_image_quality.py` | 六槽角色契约、critic 阈值、白底暗图拦截、PNG 畸形、兜底路径默认关闭 |
| `test_video_quality.py` | media_probe 全矩阵 + 生成链路本地选型、单次 POST、字幕证据绑定 |
| `test_creative_plan.py` | EDL 帧范围、帧溯源、伪造 provenance 拒绝、字幕留白 |
| `test_runtime_quality.py` | 网络前 fail-closed、预算与截止、输入解析边界、脱敏 |
| `test_studio_finish.py` | ffmpeg 本地成片（需本机具备 ffmpeg / ffprobe，否则跳过） |

测试全部离线运行，不消耗任何模型额度。

---

## 📄 许可

MIT License。调研产出基于公开网络资料综合整理。

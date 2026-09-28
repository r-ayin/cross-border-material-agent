<div align="center">

<img src="docs/screenshots/workbench-cover.png" alt="一键出海 · 跨境商品素材工作台" width="100%">

[![version](https://img.shields.io/badge/版本-1.1.0-7C3AED?style=flat-square)](agent/agent.json) [![languages](https://img.shields.io/badge/语言-EN%20·%20KO%20·%20PT-DB2777?style=flat-square)](#-一次运行产出什么) [![tests](https://img.shields.io/badge/回归测试-183%20项-059669?style=flat-square)](tests/) [![python](https://img.shields.io/badge/Python-3.12%2B-7C3AED?style=flat-square)](https://www.python.org/) [![license](https://img.shields.io/badge/许可-MIT-059669?style=flat-square)](#-许可)

**输入一件商品，输出一整套可直接上架的多语言素材。**

[English](README.en.md) · [在线预览素材工作台](#-素材工作台) · [视频是怎么做的](#-视频是怎么动起来的) · [常见问题](#-常见问题)

</div>

---

## ✨ 它能做什么

| | |
|:---:|---|
| 🛍️ | **一次生成 11 件上架素材** —— 三语商品文案、1 张白底主图、5 张详情图、1 支商品视频、1 份投放策略，文件名规范、直接可传 |
| 🌏 | **面向三大市场本地化** —— 英语（美国）、韩语（韩国）、巴西葡语（巴西），各自匹配市场文案风格，不是简单翻译 |
| 🎬 | **商品视频 + 人物实穿短视频** —— 商品展示片与 15 秒竖屏实穿律动片，动作、卡点、美感都有成套方法（见[下文](#-视频是怎么动起来的)） |
| 👀 | **先看方案，再花钱** —— 默认不联网。生成前先出一份完整创作方案（分镜、字幕、六张图的分工），零成本确认方向 |
| ✅ | **不合格的素材不出厂** —— 每件素材都经过尺寸、体积、内容完整性检查，给出「通过 / 待复核 / 不通过」明确结论 |

> 下方全部素材图均由本工具**真实生成**，示例商品为「粉色百褶半身裙」。

---

## 🖼 生成素材示例

<table>
<tr>
<td align="center" width="33%"><img src="frontend/assets/main_image.png" alt="商品主图" width="100%"><br><sub><b>商品主图</b> · 纯白底 · 2048×2048</sub></td>
<td align="center" width="33%"><img src="frontend/assets/detail_image_1.png" alt="整体展示" width="100%"><br><sub><b>整体展示</b> · 卖点呈现</sub></td>
<td align="center" width="33%"><img src="frontend/assets/detail_image_2.png" alt="工艺展示" width="100%"><br><sub><b>工艺展示</b> · 腰头细节</sub></td>
</tr>
<tr>
<td align="center" width="33%"><img src="frontend/assets/detail_image_3.png" alt="垂坠展示" width="100%"><br><sub><b>垂坠展示</b> · 面料质感</sub></td>
<td align="center" width="33%"><img src="frontend/assets/detail_image_4.png" alt="场景展示" width="100%"><br><sub><b>场景展示</b> · 真实生活场景</sub></td>
<td align="center" width="33%"><img src="frontend/assets/detail_image_5.png" alt="全貌展示" width="100%"><br><sub><b>全貌展示</b> · 完整不裁切</sub></td>
</tr>
</table>

另附商品视频与人物实穿短视频，见[素材工作台](#-素材工作台)在线浏览。

---

## 📦 一次运行产出什么

**11 件必需素材**，命名严格固定，可直接对接上架流程：

| # | 素材 | 文件 | 说明 |
|:---:|:---:|---|---|
| 1–3 | 商品文案 | `product_description_en.md` / `_ko.md` / `_pt.md` | 英 / 韩 / 巴葡 · 卖点、参数、尺码、来源六大板块 |
| 4 | 商品主图 | `main_image.png` | 纯白底 · 2048×2048 · 商品完整清晰 |
| 5–9 | 详情图 | `detail_image_1.png` – `detail_image_5.png` | 整体 / 工艺 / 垂坠 / 场景 / 全貌，各司其职不重复 |
| 10 | 商品视频 | `product_video.mp4` | 30 秒内竖屏成片 · 小于 200MB |
| 11 | 策略文档 | `strategy_document.md` | 选品卖点、图片分工、视频分镜、投放建议 |

<details>
<summary><b>同时生成的过程文件（点开查看）</b></summary>

| 文件 | 说明 |
|---|---|
| `listing.json` | 全部素材的结构化索引，方便系统对接 |
| `quality_report.json` | 每件素材的检查结果与验收结论 |
| `generation_plan.json` | 生成前的创作方案（分镜、字幕、图片分工） |
| `product_video_srt.srt` | 视频外挂字幕（不烧进画面） |
| `run_manifest.json` | 本次运行的过程记录 |

</details>

---

## 🎬 视频是怎么动起来的

工具能产两种视频：**商品展示视频**（以商品图开场，30 秒内五段式：开场钩子 → 痛点 → 产品展示 → 佐证 → 行动召唤）和 **15 秒人物实穿短视频**（1080×1920 竖屏）。两者的动作、节奏与质感都来自同一套被真实成片验证过的方法。

### 动作从哪来

- **先拍一张"动作中途"的照片** —— 人物实穿视频的第一帧不是站定摆拍，而是重心落单腿、裙摆微扬的瞬间。视频模型从动势里接着生成，开场即是律动，不会前几秒呆立。
- **16 条动作库按档位编排** —— 重心转移、顶胯定格、8 字摆胯、两步律动、肩部卡点、手臂波浪、猫步走近、慢速转身裙摆开花、留头回眸、甩发定格……每条动作都标明节拍时长与生成难度：稳定生成的直接进片，容易崩的加保护写法，必然崩的写进禁用清单。
- **三档成品模板，崩了就降档** —— 全身律动展示（首选）→ 走位互动展示 → 原地律动保底。上一档生成效果不佳就降一档重来（每档至多重试一次），保证交出去的片子可播。

### 网感从哪来

- **动-停反差制造卡点** —— 每 2.5–4 秒一个可感知变化，15 秒走"起势 → 主体 → 收尾"三大拍、全片变化不超过 5 次。干脆的定格接流畅的连贯动作，后期配上 BGM 重拍就是天然卡点。
- **对镜互动** —— 全程直视镜头，结尾回眸、撩发、微笑定格。"她对你一个人展示"的准社交感，是平台原生内容区别于广告片的关键。
- **面料动势即卖点** —— 裙摆开花 → 惯性余摆 → 垂落，完整的因果链只有运动能证明。看懂"这条裙子动起来好看"的瞬间，就是想要它的瞬间。
- **UGC 手机直出感** —— 手持 vlog 运镜、真实窗光、保留皮肤纹理与发丝细节，而不是影棚磨皮广告感。目检清单里甚至要求"保留一个不完美"。
- **15 秒完播设计** —— 结尾定格与开头动势衔接，看完即可无缝循环，把完播率和重播率做进片子里。

### 美感从哪来

- **风格随商品气质走** —— 韩系温柔、美式简洁、巴西暖调、极简影棚、杂志大片五档风格按商品信号自动匹配，粉裙配的是韩系温柔通勤。
- **构图纪律** —— 全身机位锁定不漂移，人物占画面约三分之二，动作一侧留白给走位空间，背景杂物三件以内且全部虚化。
- **真人感的分寸** —— 妆容按肤、腮红、唇、眉、眼五层白描，饰品不超过两件，配色限定在衬托商品色的范围里，杜绝"AI 塑料感"。
- **出厂前逐帧质检** —— 成片后抽帧检查：三拍是否齐全、裙摆物理是否成立、手指是否正常、脚底是否打滑、面部是否漂移、背景是否稳定、结尾是否定格在产品身上。不合格降档重做，不把崩坏的片子交给你。

---

## 🚀 快速上手

**环境要求：Python 3.12 或更高，无需安装任何依赖。**

真实生成需要 [千问平台](https://platform.qianwenai.com) 的 API Key；前两步不需要。

### 第 1 步 · 离线预演（不联网、不花钱）

```bash
cd agent
python3 agent.py --plan-only --prompt "读取 /path/to/input/ 目录下目标商品的全部信息文件，提取指定内容，按规范生成输出文件并保存至 /path/to/output/。"
```

几秒后输出目录会得到一份 `generation_plan.json`：打算生成什么、每张图怎么分工、视频怎么分镜，先看方案再决定是否生成。

### 第 2 步 · 本机演练（不联网、不花钱）

```bash
python3 tests/mock_e2e.py
```

用示例商品完整走一遍流程（模拟生成），确认环境与流程正常。

### 第 3 步 · 真实生成（消耗平台额度）

```bash
export DASHSCOPE_API_KEY="<你的 API Key>"
export DASHSCOPE_BASE_URL="https://dashscope.aliyuncs.com/api/v1"
export OPENAI_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export AGENT_ALLOW_PAID_CALLS=1        # 授权开关：不开，绝不会产生任何费用

cd agent
python3 agent.py --prompt "读取 /path/to/input/ 目录下目标商品的全部信息文件，提取指定内容，按规范生成输出文件并保存至 /path/to/output/。"
```

运行结束后查看 `quality_report.json`：每件素材是「通过」还是「待复核」一目了然。

> 💡 请使用**空的输出目录**。如果目录里已有上一轮的素材，工具会拒绝运行，避免新旧素材混淆。

### 第 4 步 · 打开素材工作台

```bash
python3 -m http.server 18765 --bind 127.0.0.1 --directory frontend
```

浏览器访问 `http://127.0.0.1:18765/workbench.html`，在线浏览、筛选、下载全部素材。

### 命令速查

| 命令 | 用途 |
|---|---|
| `agent.py --plan-only --prompt "..."` | 只出创作方案，不生成素材，不花钱 |
| `agent.py --prompt "..."` | 完整生成 11 件素材（需 API Key + 授权开关） |
| `agent.py --audit 输出目录` | 检查已有素材是否合格，不生成任何东西 |
| `agent.py --check-plan 计划.json` | 校验一份创作方案文件 |
| `agent.py --version` | 查看版本号 |

**运行结束后，程序退出码就代表结论**：`0` 全部通过 → 可直接使用；`2` 素材齐全但建议人工复核；`1` 有素材缺失或不合格。

---

## ⚙️ 配置

| 环境变量 | 何时需要 | 说明 |
|---|:---:|---|
| `DASHSCOPE_API_KEY` | 真实生成 | 千问平台的 API Key |
| `DASHSCOPE_BASE_URL` | 真实生成 | 固定为 `https://dashscope.aliyuncs.com/api/v1` |
| `OPENAI_BASE_URL` | 真实生成 | 固定为 `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `AGENT_ALLOW_PAID_CALLS=1` | 真实生成 | 付费授权开关。**不设置时工具完全断网**，配置了 Key 也不会产生费用 |

安全约定：API Key 只通过环境变量传入，不写入任何文件；日志与运行记录中自动隐去密钥信息。

---

## 🖥 素材工作台

单文件网页，零依赖，起个本地服务就能用。打开 `frontend/workbench.html`：

<img src="docs/screenshots/workbench-work.png" alt="素材工作台" width="100%">

- **素材库总览** —— 图片、视频、文案分类筛选，按语言（EN / KO / PT）过滤
- **大图预览** —— 点击任意素材查看高清大图，缩略图条快速切换
- **文案在线阅读** —— 三语文案内置排版渲染，支持一键复制全文
- **单件下载 / 整包下载** —— 按需取用，或一键打包全部素材
- 需要视频可拖动进度条时，用 `python3 tools/preview_server.py` 启动（默认 18766 端口）

---

## ✅ 素材质量承诺

| 承诺 | 说明 |
|:---:|---|
| 🚫 不编造信息 | 源数据里没有的成分、认证、参数，素材里就不会出现；尺码没有实测数据就明确标注，绝不换算凑数 |
| 📐 规格达标 | 主图白底、2048×2048；详情图各 2048×2048；视频小于 200MB；图片视频均为真实格式，扩展名与内容一致 |
| 🎬 视频真实完整 | 逐段检查视频文件完整性与真实时长，时长不足或文件损坏会被拦下 |
| 🧾 结论透明 | 每件素材给出「通过 / 待复核 / 不通过」，机器验过的和需要人看分开说清楚 |
| 🔒 费用可控 | 默认完全断网；付费生成需要单独的授权开关，杜绝意外扣费 |

---

## ❓ 常见问题

<details>
<summary><b>生成一套素材要花多少钱？</b></summary>
<br>

取决于千问平台各模型的计费标准，工具本身不额外收费。预演和演练两步（`--plan-only`、`tests/mock_e2e.py`）完全免费；真实生成会调用文本、图像、视频模型各若干次。授权开关不打开时，即使配好了 Key 也不会产生任何调用。

</details>

<details>
<summary><b>支持哪些商品？</b></summary>
<br>

内置服饰类目的类目库与属性库（66 个可映射的叶子类目，覆盖上装、下装、裙装、鞋履、配饰等）。商品信息以源数据 JSON 提供，包含标题、SKU、属性与源图即可。

</details>

<details>
<summary><b>视频是多长的？</b></summary>
<br>

两种规格：商品展示视频 30 秒以内（时间预算紧张时自动降为 15 秒方案，保证不超时、不截断）；人物实穿短视频固定 15 秒、1080×1920 竖屏，约 360 帧起步。

</details>

<details>
<summary><b>素材文件名可以改吗？</b></summary>
<br>

11 件必需素材的文件名是固定规范，不要修改——上架流程和质检报告都按这个名字索引。过程文件同理。

</details>

<details>
<summary><b>生成的素材可以直接上架吗？</b></summary>
<br>

规格层面（尺寸、白底、体积、格式）出厂即达标；内容层面机器能查的（事实一致、语言纯净、无禁用表述）都已检查。退出码 `2` 或文案标记「待复核」时，建议人工过目语义与母语感再上架。

</details>

---

## 📁 目录一览

```
cross-border-material-agent/
├── agent/          # 生成工具本体（Python 源码 + 入口）
├── tests/          # 183 项自动化回归测试，全部离线运行
├── frontend/       # 素材工作台 + 本工具真实生成的示例素材
├── docs/           # 使用文档、视频创作方法与截图
├── research/       # 市场与素材调研资料
└── README.md       # 本文件
```

## 📄 许可

MIT License。调研资料基于公开网络资料整理。

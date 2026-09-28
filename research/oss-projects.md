# 跨境电商商品素材生成 / 上架自动化 / 多模态内容生成流水线 — 开源项目盘点

> 调研时间：2026-08-28 | 搜索轮次：10 轮（GitHub API + 直接仓库查询）
> 约束背景：目标环境禁止外部工具与网络，仅可用 DashScope/千问模型族 API → **纯代码 pipeline 模式优先**

---

## 一、概览表

| # | 项目名 | Stars | 活跃度 | 架构风格 | 技术栈 | 核心相关点 |
|---|--------|-------|--------|----------|--------|-----------|
| 1 | [VidForge](https://github.com/WANGLEVY9/VidForge) | ⭐114 | 🟢 2026-08 | Agent编排+Pipeline | TypeScript/NestJS/LangGraph/FFmpeg | 短视频电商pipeline、多agent编排、RAG脚本、成本追踪 |
| 2 | [MoneyPrinterAICreate](https://github.com/q1uki/MoneyPrinterAICreate) | ⭐323 | 🟢 2026-08 | Pipeline | Python/Wan2.1 | Wan2.1文生视频+图生视频、AI分镜大纲、动态视频 |
| 3 | [Amazon-Skills](https://github.com/nexscope-ai/Amazon-Skills) | ⭐601 | 🟢 2026-08 | Agent Skills | Python | Amazon卖家AI技能集、关键词研究、Listing审计、竞品分析 |
| 4 | [ComfyUI-MultiModal-Prompt-Nodes](https://github.com/kantan-kanto/ComfyUI-MultiModal-Prompt-Nodes) | ⭐14 | 🟢 2026-08 | ComfyUI节点 | Python/Qwen | Qwen VL多模态prompt生成、Wan2.2视频prompt、本地GGUF |
| 5 | [MediaForge](https://github.com/arjun-go-go/mediaforge) | ⭐3 | 🟢 2026-08 | Agent+RAG Pipeline | Python/FastAPI/LangGraph/Milvus | 电商AI图片平台、多模态RAG、批量工作流、质量评估 |
| 6 | [MuseForge](https://github.com/tiammomo/MuseForge) | ⭐1 | 🟡 2026-07 | Local-first Pipeline | Python | 电商团队本地图像生产工作台、批量生成、结构化prompt、审核画布 |
| 7 | [Ozon-Profit-Skills](https://github.com/coral870921-source/Ozon-Profit-Skills) | ⭐20 | 🟢 2026-08 | Agent Skills | - | 跨境Listing翻译、SEO标签、图片Prompt生成、利润核算、多平台 |
| 8 | [aliexpress-auto-listing-skill](https://github.com/southernspark-nfxh/aliexpress-auto-listing-skill) | ⭐16 | 🟢 2026-08 | Browser Automation | Python/Playwright | 1688采集→店小秘ERP→速卖通发布、全自动上架 |
| 9 | [comfyui-video-ad-pipeline](https://github.com/dalai2/comfyui-video-ad-pipeline) | ⭐0 | 🟡 2026-08 | ComfyUI Pipeline | Python/FFmpeg | 产品照片→竖版视频广告、WAN 2.2 TI2V、自动烧字 |
| 10 | [rembg](https://github.com/danielgatis/rembg) | ⭐24,471 | 🟢 2026-08 | Library/CLI | Python/U²-Net | 图像背景移除（商品抠图基础组件） |
| 11 | [BiRefNet](https://github.com/ZhengPeng7/BiRefNet) | ⭐4,103 | 🟢 2026-08 | Model/Library | Python/PyTorch | 高分辨率二值分割（精细抠图，替代rembg） |
| 12 | [DiffSynth-Studio](https://github.com/modelscope/DiffSynth-Studio) | ⭐13,013 | 🟢 2026-08 | Pipeline框架 | Python/PyTorch | Diffusion模型统一推理引擎、支持Wan/FLUX/SD等、可扩展pipeline |
| 13 | [Wan2.1](https://github.com/Wan-Video/Wan2.1) | ⭐16,900 | 🟢 2026-08 | Model/Pipeline | Python/PyTorch | 大规模视频生成模型、文生视频+图生视频、DashScope兼容 |
| 14 | [PhotoMaker](https://github.com/TencentARC/PhotoMaker) | ⭐10,088 | 🟡 2026-08 | Model/Pipeline | Python/PyTorch | ID保持的人物/产品照片生成、个性化定制 |
| 15 | [superCMO-skills](https://github.com/SupercmoHQ/superCMO-skills) | ⭐31 | 🟢 2026-08 | Agent Skills | Python | UGC视频、广告视频、产品摄影、端到端营销素材生成 |
| 16 | [amazon-product-studio](https://github.com/SamurAIGPT/amazon-product-studio) | ⭐11 | 🟢 2026-08 | SaaS/Web App | Next.js/Prisma | AI产品摄影工作室、多图参考上传、预设模板、场景生成 |
| 17 | [awesome-agentic-commerce](https://github.com/MentionNetwork/awesome-agentic-commerce) | ⭐62 | 🟢 2026-08 | Awesome List | - | Agentic Commerce资源汇总、MCP服务器、协议、工具索引 |
| 18 | [gpt-image-2-for-e-commerce](https://github.com/EvoLinkAI/gpt-image-2-for-e-commerce) | ⭐31 | 🟡 2026-06 | Prompt Cookbook | - | GPT Image 2电商Prompt手册、产品图/模特试穿/社交素材批量生成 |
| 19 | [LangChain](https://github.com/langchain-ai/langchain) | ⭐145,163 | 🟢 2026-08 | Agent框架 | Python/TS | 通用Agent编排框架、多模态pipeline构建基础 |
| 20 | [CrewAI](https://github.com/crewAIInc/crewAI) | ⭐57,710 | 🟢 2026-08 | Agent框架 | Python | 多角色Agent协作框架、适合构建文案+图片+审核多agent流水线 |

---

## 二、逐项详情

### 1. VidForge ⭐⭐⭐⭐⭐ (Top Pick)
- **仓库**: https://github.com/WANGLEVY9/VidForge
- **Stars**: 114 | **Forks**: 6 | **最后更新**: 2026-08-26
- **架构**: Multi-Agent编排 + Pipeline（NestJS + LangGraph + BullMQ任务队列）
- **技术栈**: TypeScript, NestJS, React, LangGraph, FFmpeg, pgvector
- **描述**: 开源AI短视频电商pipeline。包含多模态分析、RAG脚本生成、多agent编排、FFmpeg合成、成本追踪。
- **与本任务相关点**:
  - ✅ 完整的电商短视频生成pipeline（从产品素材到成品视频）
  - ✅ 多agent架构可直接参考（分析agent、脚本agent、合成agent）
  - ✅ 成本追踪机制适合批量生产管控
  - ✅ TypeScript技术栈，易于集成
  - ⚠️ 依赖外部API（需适配为DashScope）

### 2. MoneyPrinterAICreate ⭐⭐⭐⭐⭐ (Top Pick)
- **仓库**: https://github.com/q1uki/MoneyPrinterAICreate
- **Stars**: 323 | **Forks**: 64 | **最后更新**: 2026-08-27
- **架构**: 纯Pipeline模式
- **技术栈**: Python, Wan2.1, ChatGPT/DeepSeek/Kimi LLM接口
- **描述**: 基于MoneyPrinterTurbo的AI视频生成工具，接入万相通义Wan2.1的文生视频和图生视频功能，AI自动生成分镜大纲并生成动态视频。
- **与本任务相关点**:
  - ✅ **已集成Wan2.1**（DashScope同源模型，API兼容性好）
  - ✅ 纯Python pipeline，无外部GUI依赖
  - ✅ AI分镜大纲生成 → 视频生成的完整链路
  - ✅ 中文社区活跃，文档友好
  - ✅ 最适合目标环境（DashScope API + 纯代码pipeline）

### 3. Amazon-Skills ⭐⭐⭐⭐
- **仓库**: https://github.com/nexscope-ai/Amazon-Skills
- **Stars**: 601 | **Forks**: 98 | **最后更新**: 2026-08-28
- **架构**: Agent Skills集合
- **技术栈**: Python
- **描述**: 免费AI agent技能集，面向Amazon卖家：关键词研究、竞品分析、Listing审计等。兼容OpenClaw/Claude Code/Cursor等。
- **与本任务相关点**:
  - ✅ Listing审计与优化逻辑可复用
  - ✅ 关键词研究方法论适用于多平台
  - ✅ Skills格式可作为agent能力模块参考
  - ⚠️ 偏Amazon生态，需适配速卖通/Shopee

### 4. ComfyUI-MultiModal-Prompt-Nodes ⭐⭐⭐⭐
- **仓库**: https://github.com/kantan-kanto/ComfyUI-MultiModal-Prompt-Nodes
- **Stars**: 14 | **Forks**: 6 | **最后更新**: 2026-08-22
- **架构**: ComfyUI自定义节点
- **技术栈**: Python, Qwen2.5-VL/Qwen3-VL, GGUF, llama-cpp-python
- **描述**: ComfyUI多模态prompt生成节点，专为QwenImageEdit和Wan2.2设计。支持本地LLM/GGUF模型和Qwen API进行图片和视频prompt生成与增强。
- **与本任务相关点**:
  - ✅ **原生支持Qwen VL系列**（与DashScope同族）
  - ✅ 图片+视频prompt自动生成/增强
  - ✅ 支持本地GGUF运行（离线可用）
  - ✅ Wan2.2视频prompt专用优化
  - ⚠️ ComfyUI图模式，需提取核心逻辑转为纯代码pipeline

### 5. MediaForge ⭐⭐⭐
- **仓库**: https://github.com/arjun-go-go/mediaforge
- **Stars**: 3 | **最后更新**: 2026-08-24
- **架构**: Agent + RAG Pipeline
- **技术栈**: Python, FastAPI, LangGraph, Milvus/Zilliz, Celery, Redis, Next.js, OpenRouter
- **描述**: 开源电商AI图片生成平台，含多模态RAG、AI agents、畅销品检索、产品摄影、质量评估、批量工作流。
- **与本任务相关点**:
  - ✅ 完整的电商图片生成平台架构
  - ✅ 批量工作流 + 质量评估闭环
  - ✅ RAG检索畅销品风格参考
  - ⚠️ 依赖较多外部服务（OpenRouter等），需替换为DashScope

### 6. MuseForge ⭐⭐⭐
- **仓库**: https://github.com/tiammomo/MuseForge
- **Stars**: 1 | **最后更新**: 2026-07-26
- **架构**: Local-first Pipeline + Desktop Workspace
- **技术栈**: Python
- **描述**: 面向电商团队的本地优先AI图像生产工作台。连接产品素材、结构化prompt、批量生成、实时进度追踪、候选审核、编辑画布。
- **与本任务相关点**:
  - ✅ **Local-first设计**（契合禁止外部网络约束）
  - ✅ 批量生成 + 审核筛选闭环
  - ✅ 结构化prompt管理
  - ⚠️ Star极少，成熟度待验证

### 7. Ozon-Profit-Skills ⭐⭐⭐
- **仓库**: https://github.com/coral870921-source/Ozon-Profit-Skills
- **Stars**: 20 | **最后更新**: 2026-08-24
- **架构**: Agent Skills
- **描述**: Claude Code跨境电商AI自动化技能集——Listing多语言翻译、SEO标签生成、图片Prompt生成、利润核算。适配Ozon/TikTok Shop/Amazon/AliExpress。
- **与本任务相关点**:
  - ✅ **多平台适配**（含AliExpress）
  - ✅ Listing翻译 + SEO标签 + 图片Prompt三位一体
  - ✅ 中文文档，跨境电商场景贴合
  - ⚠️ Skills格式，需提取核心逻辑

### 8. aliexpress-auto-listing-skill ⭐⭐⭐
- **仓库**: https://github.com/southernspark-nfxh/aliexpress-auto-listing-skill
- **Stars**: 16 | **最后更新**: 2026-08-26
- **架构**: Browser Automation Pipeline
- **技术栈**: Python, Playwright
- **描述**: 速卖通自动上架工作流：1688采集 → 店小秘ERP → 速卖通发布。AI浏览器自动化实现跨境电商全流程。
- **与本任务相关点**:
  - ✅ **速卖通上架全流程自动化**（最直接相关）
  - ✅ 1688货源采集 + ERP对接
  - ⚠️ 浏览器自动化模式，非纯API pipeline
  - ⚠️ 依赖店小秘ERP账号

### 9. comfyui-video-ad-pipeline ⭐⭐
- **仓库**: https://github.com/dalai2/comfyui-video-ad-pipeline
- **Stars**: 0 | **最后更新**: 2026-08-08
- **架构**: ComfyUI Pipeline + FFmpeg后处理
- **技术栈**: Python, ComfyUI WAN 2.2, FFmpeg
- **描述**: 将产品照片转化为完成的竖版视频广告：通过HTTP API驱动ComfyUI WAN 2.2 TI2V工作流，再用FFmpeg后处理为1080x1920并烧入钩子文字。
- **与本任务相关点**:
  - ✅ **产品照片→视频广告的完整pipeline**
  - ✅ WAN 2.2 TI2V（图生视频）
  - ✅ FFmpeg后处理（分辨率+字幕烧入）
  - ✅ 纯代码可提取（HTTP API调用ComfyUI）
  - ⚠️ 需要ComfyUI后端运行

### 10. rembg ⭐⭐⭐⭐ (基础设施)
- **仓库**: https://github.com/danielgatis/rembg
- **Stars**: 24,471 | **最后更新**: 2026-08-28
- **架构**: Library / CLI工具
- **技术栈**: Python, U²-Net, ONNX
- **描述**: 图像背景移除工具，支持CLI/API/HTTP服务多种调用方式。
- **与本任务相关点**:
  - ✅ 商品抠图的标准工具
  - ✅ 纯Python库，可嵌入任何pipeline
  - ✅ 支持批量处理
  - ✅ 离线运行，无外部依赖

### 11. BiRefNet ⭐⭐⭐ (基础设施)
- **仓库**: https://github.com/ZhengPeng7/BiRefNet
- **Stars**: 4,103 | **最后更新**: 2026-08-28
- **架构**: Model / Library
- **技术栈**: Python, PyTorch
- **描述**: 双边参考高分辨率二值图像分割模型，精度优于rembg。
- **与本任务相关点**:
  - ✅ 高精度商品抠图（尤其复杂边缘）
  - ✅ 可作为rembg的升级替代
  - ✅ 支持高分辨率输入

### 12. DiffSynth-Studio ⭐⭐⭐⭐⭐ (Top Pick)
- **仓库**: https://github.com/modelscope/DiffSynth-Studio
- **Stars**: 13,013 | **最后更新**: 2026-08-28
- **架构**: Pipeline框架 / 统一推理引擎
- **技术栈**: Python, PyTorch
- **描述**: ModelScope出品的Diffusion模型统一推理引擎，支持Wan/FLUX/SD/SDXL等多模型，提供可扩展的pipeline抽象。
- **与本任务相关点**:
  - ✅ **ModelScope出品**（阿里系，与DashScope天然兼容）
  - ✅ 统一pipeline框架，一套代码跑多种生成模型
  - ✅ 原生支持Wan视频生成模型
  - ✅ 纯Python代码pipeline，无GUI依赖
  - ✅ 社区活跃，持续维护
  - ✅ 最适合构建统一的多模态生成pipeline基座

### 13. Wan2.1 ⭐⭐⭐⭐⭐ (核心模型)
- **仓库**: https://github.com/Wan-Video/Wan2.1
- **Stars**: 16,900 | **最后更新**: 2026-08-28
- **架构**: Model + Pipeline
- **技术栈**: Python, PyTorch
- **描述**: 开放的大规模视频生成模型，支持文生视频和图生视频。
- **与本任务相关点**:
  - ✅ **DashScope API直接可用的同款模型**
  - ✅ 文生视频 + 图生视频双模式
  - ✅ 开源权重可本地部署（备选方案）
  - ✅ 电商短视频生成的核心引擎

### 14. PhotoMaker ⭐⭐⭐
- **仓库**: https://github.com/TencentARC/PhotoMaker
- **Stars**: 10,088 | **最后更新**: 2026-08-26
- **架构**: Model / Pipeline
- **技术栈**: Python, PyTorch, Stable Diffusion
- **描述**: CVPR 2024，ID保持的个性化照片生成，可将特定人物/产品融入新场景。
- **与本任务相关点**:
  - ✅ 产品一致性保持（同一产品在不同场景中外观一致）
  - ✅ 可用于生成模特展示图
  - ⚠️ 基于SD，非DashScope原生

### 15. superCMO-skills ⭐⭐⭐
- **仓库**: https://github.com/SupercmoHQ/superCMO-skills
- **Stars**: 31 | **最后更新**: 2026-08-27
- **架构**: Agent Skills集合
- **技术栈**: Python
- **描述**: 开源AI营销技能集，赋能任意AI agent生成端到端营销素材——UGC视频、广告视频、产品摄影等。
- **与本任务相关点**:
  - ✅ 端到端营销素材生成（视频+图片）
  - ✅ Agent Skills格式，模块化可插拔
  - ✅ 支持多种agent平台

### 16. amazon-product-studio ⭐⭐
- **仓库**: https://github.com/SamurAIGPT/amazon-product-studio
- **Stars**: 11 | **最后更新**: 2026-08-22
- **架构**: SaaS Web App
- **技术栈**: Next.js, Prisma, Stripe, TailwindCSS
- **描述**: 开源AI产品摄影工作室SaaS，支持多图参考上传、预设模板、Webhook场景生成。Flair AI / Booth AI的免费替代。
- **与本任务相关点**:
  - ✅ 产品摄影场景化生成的完整参考实现
  - ✅ 模板系统可复用
  - ⚠️ SaaS架构，需大幅改造为pipeline模式

### 17. awesome-agentic-commerce ⭐⭐⭐ (索引)
- **仓库**: https://github.com/MentionNetwork/awesome-agentic-commerce
- **Stars**: 62 | **最后更新**: 2026-08-26
- **架构**: Awesome List / 资源索引
- **描述**: Agentic Commerce资源大全——协议、MCP服务器、工具、应用、API和服务。面向店主、开发者、代理商和营销人员。
- **与本任务相关点**:
  - ✅ 发现更多工具和资源的入口
  - ✅ MCP服务器列表（可能与DSH集成）
  - ✅ 覆盖Shopify/WooCommerce/BigCommerce等多平台

### 18. gpt-image-2-for-e-commerce ⭐⭐⭐
- **仓库**: https://github.com/EvoLinkAI/gpt-image-2-for-e-commerce
- **Stars**: 31 | **最后更新**: 2026-06-30
- **架构**: Prompt Cookbook / 最佳实践
- **描述**: GPT Image 2电商使用指南——产品listing照片、模特试穿、产品展示、互动场景、社交电商创意。支持Evolink API批量生成。
- **与本任务相关点**:
  - ✅ 电商图片prompt最佳实践手册
  - ✅ 覆盖多种电商场景的prompt模板
  - ✅ 批量生成方法论
  - ⚠️ 针对GPT Image 2，prompt需适配千问图像模型

### 19. LangChain ⭐⭐⭐ (框架基础)
- **仓库**: https://github.com/langchain-ai/langchain
- **Stars**: 145,163 | **最后更新**: 2026-08-28
- **架构**: Agent编排框架
- **技术栈**: Python, TypeScript
- **描述**: Agent工程平台，支持模块化pipeline和agent工作流构建。
- **与本任务相关点**:
  - ✅ 成熟的pipeline编排基础设施
  - ✅ 多模态支持
  - ⚠️ 较重，对于纯DashScope场景可能过度工程化

### 20. CrewAI ⭐⭐⭐ (框架基础)
- **仓库**: https://github.com/crewAIInc/crewAI
- **Stars**: 57,710 | **最后更新**: 2026-08-28
- **架构**: 多角色Agent协作框架
- **技术栈**: Python
- **描述**: 角色扮演自主AI agent协作框架，适合构建文案撰写+图片生成+质量审核的多agent流水线。
- **与本任务相关点**:
  - ✅ 多角色分工模式（文案agent、图片agent、审核agent）
  - ✅ 适合构建端到端内容生产团队
  - ⚠️ 同样较重

---

## 三、纯代码 Pipeline 模式专项推荐

> 以下项目最适合「禁止外部工具与网络、仅DashScope API」的目标环境：

| 优先级 | 项目 | 理由 |
|--------|------|------|
| 🥇 | **MoneyPrinterAICreate** | 已集成Wan2.1（DashScope同源）、纯Python pipeline、AI分镜→视频全链路、中文社区 |
| 🥈 | **DiffSynth-Studio** | ModelScope出品（阿里系）、统一pipeline框架、原生支持Wan/FLUX、可扩展性强 |
| 🥉 | **ComfyUI-MultiModal-Prompt-Nodes** | 原生Qwen VL支持、图片+视频prompt生成、可提取核心逻辑脱离ComfyUI |
| 4 | **VidForge** | 完整电商视频pipeline架构参考、多agent编排模式、TypeScript技术栈 |
| 5 | **rembg / BiRefNet** | 商品抠图基础组件、纯库形式、零外部依赖 |

---

## 四、建议的技术选型组合

针对「跨境电商商品素材生成 + DashScope only」场景，推荐的开源组件组合：

```
┌─────────────────────────────────────────────────┐
│              跨境电商素材生成 Pipeline             │
├─────────────────────────────────────────────────┤
│                                                   │
│  文案层: Qwen3.7-max (DashScope API)             │
│    ├── 多语言标题/描述生成                         │
│    ├── SEO关键词提取                               │
│    └── 类目属性映射                                │
│                                                   │
│  图片层:                                          │
│    ├── 抠图: rembg / BiRefNet (本地)              │
│    ├── 主图生成: qwen-image-3.0-pro (DashScope)   │
│    ├── 详情图: wan2.7-image (DashScope)           │
│    └── Prompt优化: Qwen VL (参考MultiModal Nodes) │
│                                                   │
│  视频层:                                          │
│    ├── 图生视频: wan2.7-i2v (DashScope)           │
│    ├── 文生视频: Wan2.1 (DashScope)               │
│    └── 后处理: FFmpeg (本地)                       │
│                                                   │
│  编排层:                                          │
│    ├── Pipeline框架: DiffSynth-Studio             │
│    ├── Agent编排: 参考VidForge多agent模式         │
│    └── 批量调度: 参考MuseForge local-first设计     │
│                                                   │
└─────────────────────────────────────────────────┘
```

---

## 五、来源链接汇总

1. https://github.com/WANGLEVY9/VidForge
2. https://github.com/q1uki/MoneyPrinterAICreate
3. https://github.com/nexscope-ai/Amazon-Skills
4. https://github.com/kantan-kanto/ComfyUI-MultiModal-Prompt-Nodes
5. https://github.com/arjun-go-go/mediaforge
6. https://github.com/tiammomo/MuseForge
7. https://github.com/coral870921-source/Ozon-Profit-Skills
8. https://github.com/southernspark-nfxh/aliexpress-auto-listing-skill
9. https://github.com/dalai2/comfyui-video-ad-pipeline
10. https://github.com/danielgatis/rembg
11. https://github.com/ZhengPeng7/BiRefNet
12. https://github.com/modelscope/DiffSynth-Studio
13. https://github.com/Wan-Video/Wan2.1
14. https://github.com/TencentARC/PhotoMaker
15. https://github.com/SupercmoHQ/superCMO-skills
16. https://github.com/SamurAIGPT/amazon-product-studio
17. https://github.com/MentionNetwork/awesome-agentic-commerce
18. https://github.com/EvoLinkAI/gpt-image-2-for-e-commerce
19. https://github.com/langchain-ai/langchain
20. https://github.com/crewAIInc/crewAI

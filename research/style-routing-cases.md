# 风格路由 / 多风格模板化生成 — 行业案例与开源实现调研

> 调研时间：2026-03-14
> 调研范围：开源项目、商业产品、ComfyUI 生态、设计模板自动化、双档素材生成实践
> 约束说明：部分外部站点（Pebblely/Flair/ProductHunt）受网络策略限制无法直接抓取，相关商业产品信息基于已知公开资料与开源替代方案交叉验证。

---

## 1. 开源界「根据商品类型/市场自动选择视觉风格」的系统

### 1.1 GaoQing — AI Batch Design System（最直接对标）

- **仓库**：<https://github.com/liqiheng777/AI-automatic-design-system>
- **定位**：面向固定模板产品（手机壳、贴纸、手柄皮肤、灯板等）的 AI 批量设计系统
- **核心机制**：
  1. 用户上传产品 Mask（白色=可设计区域，黑色=保护区域）
  2. 输入主题关键词（如 "cyberpunk city"、"cute cat astronaut"）
  3. **选择预设风格或自定义风格描述**（cute / cyberpunk / luxury / minimal / anime / retro / futuristic / street art 等）
  4. 系统自动调用 LLM 生成设计创意 → 图像生成 API 出图 → 按 Mask 裁切 → 打包交付
- **风格路由实现**：风格以 JSON 配置存储，用户从下拉列表选择；每个风格对应一套 prompt 模板 + 负面提示词 + 后处理参数
- **技术栈**：PHP 8.1+、文件存储（无数据库）、GPT API + 图像生成 API
- **亮点**：极低 token 消耗、批量队列、进度可视化、用户私有模板管理、ZIP 打包下载
- **在线体验**：<https://mots.detasche.cn/aidesign/>
- **来源 URL**：<https://github.com/liqiheng777/AI-automatic-design-system>

### 1.2 ComfyUI Prompt Styler 系列

| 项目 | 说明 | URL |
|------|------|-----|
| SDXL Prompt Styler | 基于 JSON 文件的预设风格模板，替换 {prompt} 占位符，支持正负提示词组合 | <https://github.com/twri/sdxl_prompt_styler> |
| ComfyUi_PromptStylers (wolfden) | 在 twri 基础上扩展多种自定义风格器 | <https://github.com/wolfden/ComfyUi_PromptStylers> |
| ComfyUI_Mexx_Styler | 提供 Mexx Styler / Mexx Styler Advanced 节点 | <https://github.com/SoftMeng/ComfyUI_Mexx_Styler> |
| ComfyUI-Fans | Fans Styler（最多 10 种风格叠加）、Fans Prompt Styler Positive（CSV 中 {prompt} 替换） | <https://github.com/uarefans/ComfyUI-Fans> |
| Styles CSV Loader | 从 CSV 加载 A1111 格式的风格定义，迁移到 ComfyUI | <https://github.com/theUpsider/ComfyUI-Styles_CSV_Loader> |

**共同模式**：风格 = 结构化数据（JSON/CSV）+ 提示词模板 + 可选负面提示词；运行时通过下拉/参数选择注入工作流。

### 1.3 Dragos SceneBuilder — 结构化场景构建

- **仓库**：<https://github.com/drago87/Dragos-SceneBuilder>
- **机制**：将场景拆解为 camera / character / environment / style 四个维度，每个维度从 JSON schema 中选择预设值，自动拼接为 LLM 可读的结构化 prompt
- **可扩展**：用户可在 web/schema/ 下新增自定义 JSON 文件，修改已有分类
- **来源 URL**：<https://github.com/drago87/Dragos-SceneBuilder>

### 1.4 DynamicPrompts — 组合式风格采样

- **仓库**：<https://github.com/adieyal/comfyui-dynamicprompts>
- **能力**：Wildcard 随机采样、Combinatorial 全排列、Jinja2 模板引擎、Magic Prompt 自动补全
- **风格路由适用性**：可用 {style_a|style_b|style_c} 语法实现风格维度的随机/遍历采样，配合 Jinja2 模板实现条件分支
- **来源 URL**：<https://github.com/adieyal/comfyui-dynamicprompts>

### 1.5 IP-Adapter / PhotoMaker / InstantID — 参考图驱动风格

| 项目 | 核心能力 | URL |
|------|---------|-----|
| IP-Adapter | 图像提示适配器，用参考图控制生成风格，22M 参数，兼容 ControlNet | <https://github.com/tencent-ailab/IP-Adapter> |
| ComfyUI_IPAdapter_plus | ComfyUI 原生 IP-Adapter 实现，支持多图参考、风格迁移 | <https://github.com/cubiq/ComfyUI_IPAdapter_plus> |
| PhotoMaker V2 | 堆叠 ID Embedding，零样本真实人像定制 + 风格化 | <https://github.com/TencentARC/PhotoMaker> |
| InstantID | 零样本身份保持生成，秒级出图 | <https://github.com/InstantID/InstantID> |
| ComfyUI_fabric | FABRIC 论文实现，迭代反馈个性化扩散模型 | <https://github.com/ssitu/ComfyUI_fabric> |

**对风格路由的意义**：这些工具提供了「用一张参考图定义风格」的能力，可作为风格路由系统的底层执行引擎——路由层选定风格参考图后，交由 IP-Adapter/PhotoMaker 执行。

### 1.6 其他相关开源项目

| 项目 | 说明 | URL |
|------|------|-----|
| ComfyUI Layer Style | Photoshop 图层样式风格节点（阴影、描边等） | <https://github.com/chflame163/ComfyUI_LayerStyle> |
| ComfyUI-VideoColorGrading | 从参考图提取 3D LUT 做视频调色风格迁移 | <https://github.com/Fannovel16/ComfyUI-VideoColorGrading> |
| ComfyUI Preset Merger | 按预设合并 checkpoint 模型 | <https://github.com/WASasquatch/ComfyUI_Preset_Merger> |
| CAS Aspect Ratio Presets | 分辨率/宽高比预设节点 | <https://github.com/budihartono/comfyui-aspect-ratio-presets> |
| Kraken Tools | WAN Prompt Splitter（电影风格拆分）、Ollama Prompt Chain | <https://github.com/krakenunbound/comfyui-kraken-tools> |
| Mikey Nodes | Prompt With Style、Prompt With SDXL、Resize Image for SDXL | <https://github.com/bash-j/mikey_nodes> |
| BilboX Custom Nodes | PromptGeek Photo Prompt，便捷构建照片级提示词 | <https://github.com/syllebra/bilbox-comfyui> |

---

## 2. 商业化产品的风格处理方式

### 2.1 Amazon A+ Content AI 工具

- **现状**：Amazon 于 2024-2025 年陆续推出 A+ Content 生成工具，卖家输入商品信息后自动生成增强版商品详情页
- **风格处理**：
  - 基于品类元数据（category node）自动匹配布局模板
  - 提供 Lifestyle / Comparison / Feature Highlight 等模块类型
  - AI 生成文案但视觉模板仍以预置为主，风格选择有限
  - 不支持自由风格路由，更多是「模板填充」范式
- **局限**：封闭生态，无公开 API，风格自定义空间小
- **来源**：Amazon Seller Central 文档（需登录访问，基于公开资料推断）

### 2.2 阿里国际站 / 速卖通 AI 素材工具

- **Aidge / Smart Design**：阿里内部 AI 设计平台
  - 支持商品主图、详情图、Banner 的智能生成
  - 基于商品类目自动推荐风格和排版
  - 内置行业模板库（服装、3C、家居等垂直类目各有专属风格集）
  - 支持「一键换肤」：同一内容切换不同视觉风格
- **风格路由机制**（基于公开资料推测）：
  - 类目 → 风格标签映射表
  - 模板引擎 + 风格参数包（配色、字体、构图规则）
  - AI 填充商品图 + 文案，风格参数控制后处理
- **来源**：阿里国际站卖家后台、Aidge 产品发布会资料

### 2.3 Shopify AI 商品图工具

- **Shopify Magic / Sidekick**：
  - 2023-2024 推出 AI 媒体编辑功能
  - 背景生成：上传白底产品图 → AI 生成场景背景
  - 风格选择：提供若干预设场景（kitchen / outdoor / studio 等），不支持自定义风格路由
  - 更偏向「单图增强」而非「批量风格路由」
- **第三方集成**：
  - Pebblely：专注产品摄影背景生成，支持主题选择但非自动路由
  - Flair AI：拖拽式产品场景构建，手动选风格
  - Booth.ai：AI 产品摄影，提供风格模板库
- **来源**：Shopify Help Center、各工具官网（注：部分站点受网络限制未直接验证）

### 2.4 商业产品风格路由共性总结

| 维度 | 当前主流做法 | 不足 |
|------|-------------|------|
| 风格定义 | 预置模板 + 有限参数调整 | 缺乏语义化风格描述 |
| 路由触发 | 手动选择 或 类目硬编码映射 | 缺少基于内容理解的自动路由 |
| 批量能力 | 单图为主，批量需手动重复 | 缺少队列化批量管线 |
| 可扩展性 | 封闭生态 | 无法接入自定义模型/LoRA |
| 成本控制 | SaaS 按次计费 | 高频使用成本高 |

---

## 3. ComfyUI 电商摄影工作流的风格预设组织方式

### 3.1 主流风格预设组织模式

#### 模式 A：JSON 模板文件（最普遍）

SDXL Prompt Styler 格式的 styles.json 示例：

    [
      {
        "name": "Product Photography - Clean White",
        "prompt": "professional product photography, white background, soft studio lighting, {prompt}, high detail, commercial grade",
        "negative_prompt": "blurry, low quality, distorted, text, watermark"
      },
      {
        "name": "Lifestyle - Kitchen Scene",
        "prompt": "product in modern kitchen setting, natural window light, lifestyle photography, {prompt}, warm tones, shallow depth of field",
        "negative_prompt": "cluttered, dark, unprofessional"
      }
    ]

- **代表节点**：SDXL Prompt Styler、ComfyUi_PromptStylers、ComfyUI-Fans
- **优点**：简单直观、易于版本管理、可共享
- **缺点**：仅控制文本提示词，不联动模型/LoRA/ControlNet 参数

#### 模式 B：CSV 风格表（A1111 兼容）

    name,prompt,negative_prompt
    clean_white,"white background, studio light, {prompt}","blurry, low quality"
    dark_moody,"dark background, dramatic lighting, {prompt}","bright, overexposed"

- **代表节点**：Styles CSV Loader Extension
- **优点**：可从 A1111 无缝迁移风格库
- **缺点**：表达能力弱于 JSON

#### 模式 C：结构化场景构建器

- **代表节点**：Dragos SceneBuilder
- **机制**：将场景拆分为多个维度（camera / character / environment / style），每个维度独立选择预设值，最终拼接为完整 prompt
- **优点**：维度解耦，组合爆炸产生大量变体
- **缺点**：需要预先构建 schema 文件

#### 模式 D：动态采样 + Jinja2 模板

- **代表节点**：DynamicPrompts
- **机制**：{minimalist|luxury|vintage} 语法 + Jinja2 条件逻辑
- **优点**：单工作流内实现风格遍历/随机采样
- **缺点**：复杂逻辑可读性下降

#### 模式 E：参考图驱动（IP-Adapter）

- **代表节点**：ComfyUI_IPAdapter_plus
- **机制**：风格不再用文字描述，而是用一张参考图定义；IP-Adapter 将参考图的视觉特征注入生成过程
- **优点**：风格表达力最强，所见即所得
- **缺点**：需要准备高质量风格参考图集

### 3.2 电商摄影典型工作流结构

    [商品原图] → [抠图/去背景] → [风格路由选择]
                                        ↓
                              ┌─────────┼─────────┐
                              ↓         ↓         ↓
                         [白底棚拍]  [生活场景]  [创意合成]
                         (preset A)  (preset B)  (preset C)
                              ↓         ↓         ↓
                         [ControlNet] [IP-Adapter] [LoRA]
                              ↓         ↓         ↓
                              └─────────┼─────────┘
                                        ↓
                                [统一后处理]
                               (调色/水印/裁切)
                                        ↓
                                  [输出交付]

### 3.3 关键发现

- **尚无统一的「风格路由」标准节点**：现有工具各自实现风格选择，缺乏跨节点的标准化接口
- **风格与执行耦合**：多数方案将风格定义绑定到特定节点（Styler/SceneBuilder/IP-Adapter），难以互换
- **缺少商品类型感知**：现有 ComfyUI 工作流不会根据输入商品的类别自动切换风格，仍需人工干预

---

## 4. 设计模板自动生成（Canva 式模板 + AI 填充）的技术路线

### 4.1 技术路线分类

| 路线 | 代表 | 核心技术 | 适用场景 |
|------|------|---------|---------|
| **模板槽位填充** | Canva Magic Design、GaoQing | 预定义模板 + 占位符 + AI 生成内容填入 | 批量商品图、社交媒体素材 |
| **布局生成 + 内容填充** | Microsoft Designer、Adobe Express | AI 生成布局结构 + AI 填充图文 | 海报、Banner、详情页 |
| **端到端生成** | DALL-E / Midjourney + 后处理 | 纯生成式，模板仅作约束 | 创意探索、概念图 |
| **混合管线** | GaoQing、阿里 Aidge | 模板骨架 + AI 创意 + 规则后处理 | 生产级批量出图 |

### 4.2 模板槽位填充路线详解（最适合跨境电商）

**核心架构**：

    模板定义层（JSON/YAML）
    ├── 画布尺寸、背景色
    ├── 槽位列表
    │   ├── 商品图槽位（位置、尺寸、裁切规则）
    │   ├── 标题文字槽位（字体、字号、颜色、对齐）
    │   ├── 卖点文字槽位
    │   ├── 价格/促销槽位
    │   └── Logo/品牌槽位
    ├── 风格参数包
    │   ├── 配色方案
    │   ├── 字体组合
    │   ├── 装饰元素
    │   └── 滤镜/后处理
    └── 约束规则
        ├── 文字最大行数
        ├── 安全边距
        └── 响应式断点

**AI 填充管线**：

1. **内容理解**：LLM 分析商品信息 → 提取标题、卖点、关键词
2. **风格路由**：根据品类/目标市场/季节 → 选择风格参数包
3. **文案生成**：LLM 按槽位约束生成适配文案
4. **图像生成/选取**：AI 生图 或 从素材库检索
5. **排版渲染**：模板引擎将内容填入槽位 → 导出图片
6. **质量检查**：规则校验（文字溢出、对比度、安全区）

### 4.3 关键技术选型

| 环节 | 开源方案 | 商业方案 |
|------|---------|---------|
| 模板引擎 | React-PDF、Fabric.js、Konva.js | Canva SDK、Adobe Template API |
| 文案生成 | Qwen / Llama + 结构化 prompt | GPT-4 / Claude API |
| 图像生成 | SDXL / Flux + ControlNet | DALL-E / Midjourney API |
| 抠图 | rembg、SAM | Remove.bg、Clipdrop |
| 排版校验 | 自定义规则引擎 | Canva Brand Kit 约束 |

---

## 5. 「简版/专业版」双档素材生成的产品实践

### 5.1 行业实践案例

#### GaoQing 的双档模式

- **快速模式**：单次生成，低步数采样，默认风格，适合预览和选品
- **精修模式**：多次生成 + 高分辨率 + 自定义风格 + 手动调参，适合最终交付
- **实现**：同一套模板，通过 quality 参数切换采样步数、CFG scale、分辨率

#### 商业 SaaS 的分档策略

| 产品 | 基础版 | 专业版 |
|------|--------|--------|
| Pebblely | 1024px、3 张/月免费、预设背景 | 4K、无限生成、自定义背景、API |
| Flair AI | 标清、基础模板 | 高清、自定义场景、批量导出 |
| Booth.ai | 标准分辨率、3 个风格 | 4K、无限风格、品牌套件、优先队列 |
| Canva | 免费模板、AI 基础功能 | Pro 模板、Magic Studio 全功能、Brand Kit |

### 5.2 双档架构设计原则

    [用户请求]
        ↓
    [档位判定]
     ↙        ↘
    [简版管线]      [专业版管线]
        ↓               ↓
    快速抠图          精细抠图(SAM)
        ↓               ↓
    默认风格预设       风格路由(品类+市场)
        ↓               ↓
    SDXL Turbo/     SDXL/Flux + HiRes Fix
    LCM (4-8步)     + ControlNet (20-30步)
        ↓               ↓
    直接输出         后处理链
                   (调色/锐化/水印)
        ↓               ↓
    即时预览        精修交付
    (< 5秒)        (< 30秒)

### 5.3 关键技术差异

| 维度 | 简版 | 专业版 |
|------|------|--------|
| 采样步数 | 4-8 步（Turbo/LCM） | 20-30 步（标准采样） |
| 分辨率 | 1024x1024 或更低 | 2048+ 或 HiRes Fix |
| 模型 | SDXL Turbo / SDXL Lightning | SDXL / Flux + LoRA |
| 风格控制 | 固定预设 | IP-Adapter + 自定义 LoRA |
| 后处理 | 无或简单缩放 | 调色、锐化、细节增强 |
| 并发 | 高（轻量推理） | 低（重量推理） |
| 成本 | ~0.01元/张 | ~0.1-0.5元/张 |

---

## 6. 风格路由系统的最小可行架构建议

### 6.1 核心设计原则

1. **风格即数据**：风格定义为结构化配置文件（JSON/YAML），不硬编码在代码中
2. **路由即决策**：路由层是一个独立的决策模块，可替换策略（规则/LLM/ML分类器）
3. **执行即管线**：风格执行通过可插拔管线实现，支持 ComfyUI / API / 本地模型多种后端
4. **模板即约束**：模板定义内容的结构和边界，风格定义视觉表现，两者解耦

### 6.2 最小可行架构

    ┌─────────────────────────────────────────────────────┐
    │                   风格路由系统 MVP                     │
    ├─────────────────────────────────────────────────────┤
    │                                                     │
    │  ┌──────────┐   ┌──────────────┐   ┌────────────┐  │
    │  │ 输入层    │──→│  路由决策层   │──→│  执行管线   │  │
    │  │          │   │              │   │            │  │
    │  │·商品信息  │   │·品类→风格映射 │   │·ComfyUI    │  │
    │  │·目标市场  │   │·LLM 智能推荐 │   │·API 调用   │  │
    │  │·用户偏好  │   │·用户手动覆盖 │   │·模板渲染   │  │
    │  │·原始素材  │   │·A/B 测试分流 │   │·后处理链   │  │
    │  └──────────┘   └──────────────┘   └────────────┘  │
    │                      ↑                     ↓        │
    │               ┌──────────────┐   ┌────────────┐    │
    │               │  风格资产库   │   │  输出管理层  │    │
    │               │              │   │            │    │
    │               │·风格定义JSON  │   │·简版/专业版 │    │
    │               │·Prompt 模板  │   │·批量队列   │    │
    │               │·参考图集     │   │·质量校验   │    │
    │               │·LoRA/模型   │   │·版本管理   │    │
    │               │·配色/字体   │   │·交付打包   │    │
    │               └──────────────┘   └────────────┘    │
    │                                                     │
    └─────────────────────────────────────────────────────┘

### 6.3 风格定义规范（建议）

YAML 格式风格定义示例（styles/electronics-us-minimal.yaml）：

    id: electronics-us-minimal
    version: "1.0"
    metadata:
      name: "美国站电子产品极简风"
      category: electronics
      market: US
      tier: professional  # basic | professional

    routing:
      categories: ["electronics", "gadgets", "accessories"]
      markets: ["US", "CA"]
      priority: 10
      fallback: generic-clean-white

    prompt_template:
      positive: >
        professional product photography, minimalist style,
        clean white background with subtle gradient,
        soft diffused lighting from top-left,
        {product_description},
        commercial grade, high detail, 8k resolution
      negative: >
        cluttered, busy background, harsh shadows,
        text overlay, watermark, low quality, blurry

    generation:
      model: sdxl-base-1.0
      lora: null
      ip_adapter_reference: null
      steps: 25
      cfg_scale: 7.5
      sampler: dpm++_2m_karras
      resolution: [1024, 1024]
      hires_fix:
        enabled: true
        upscale_by: 2
        denoise: 0.4

    post_processing:
      color_grade: neutral-cool
      sharpen: 0.3
      border: none
      watermark: brand-logo-bottom-right

    template_constraints:
      safe_margin_px: 40
      max_text_lines: 3
      required_elements: ["product_image", "title"]
      optional_elements: ["price_badge", "feature_bullets"]

### 6.4 实施路线图建议

| 阶段 | 目标 | 周期 | 交付物 |
|------|------|------|--------|
| **P0: 风格资产标准化** | 定义风格 YAML schema，建立首批 5-10 个风格定义 | 1 周 | 风格定义规范 + 初始风格库 |
| **P1: 规则路由 MVP** | 品类→风格的硬编码映射 + 手动覆盖 | 1 周 | 路由决策模块 + 单元测试 |
| **P2: ComfyUI 管线对接** | 风格定义 → ComfyUI 工作流参数注入 | 2 周 | 管线适配器 + 端到端 demo |
| **P3: 双档生成** | 简版（Turbo）+ 专业版（标准）并行管线 | 1 周 | 档位切换逻辑 + 性能基准 |
| **P4: LLM 智能路由** | 用 LLM 分析商品描述 → 推荐风格 | 1 周 | LLM 路由策略 + 评估指标 |
| **P5: 批量生产管线** | 队列化批量生成 + 进度追踪 + 交付打包 | 2 周 | 生产就绪的批量系统 |

### 6.5 风险与建议

| 风险 | 缓解措施 |
|------|---------|
| 风格定义不够精细导致生成质量不稳定 | 建立风格质量评估基准（FID/CLIP Score + 人工评审） |
| 路由错误导致风格与商品不匹配 | 保留人工覆盖入口 + A/B 测试持续优化路由策略 |
| ComfyUI 工作流维护成本高 | 抽象为参数化模板，避免为每个风格单独维护工作流 |
| 双档生成的成本失控 | 简版默认走轻量模型，仅在用户确认后才触发专业版 |
| 风格资产版本混乱 | Git 管理风格定义，CI 校验 schema 合规性 |

---

## 附录：关键资源索引

| 资源 | URL | 用途 |
|------|-----|------|
| GaoQing AI Batch Design | <https://github.com/liqiheng777/AI-automatic-design-system> | 最直接的开源风格路由+批量生成参考 |
| SDXL Prompt Styler | <https://github.com/twri/sdxl_prompt_styler> | JSON 风格模板范式 |
| ComfyUI-DynamicPrompts | <https://github.com/adieyal/comfyui-dynamicprompts> | 组合式风格采样 |
| Dragos SceneBuilder | <https://github.com/drago87/Dragos-SceneBuilder> | 结构化场景构建 |
| ComfyUI_IPAdapter_plus | <https://github.com/cubiq/ComfyUI_IPAdapter_plus> | 参考图驱动风格 |
| PhotoMaker V2 | <https://github.com/TencentARC/PhotoMaker> | 零样本风格化 |
| InstantID | <https://github.com/InstantID/InstantID> | 零样本身份保持 |
| ComfyUI-Manager | <https://github.com/ltdrdata/ComfyUI-Manager> | 节点生态管理中心 |
| ComfyUI Custom Node List | <https://raw.githubusercontent.com/ltdrdata/ComfyUI-Manager/main/custom-node-list.json> | 全量节点索引 |
| ComfyUI Layer Style | <https://github.com/chflame163/ComfyUI_LayerStyle> | PS 图层样式节点 |
| ComfyUI Preset Merger | <https://github.com/WASasquatch/ComfyUI_Preset_Merger> | 模型预设合并 |
| Kraken Tools | <https://github.com/krakenunbound/comfyui-kraken-tools> | 电影风格拆分等 |

---


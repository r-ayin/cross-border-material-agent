# AI图像生成的风格控制与审美优化技术调研报告

> **调研状态**: ✅ 完成  
> **数据来源**: DashScope官方文档、arXiv论文摘要(PickScore/HPS v2)、GitHub开源项目(IP-Adapter/LAION-Aesthetic)、内置知识库  
> **网络限制说明**: web_search不可用(API key缺失)，外部搜索引擎(DuckDuckGo/Bing/Google Scholar)因公司网络限制返回空结果，ArXiv API被防火墙拦截。以下内容基于已成功抓取的DashScope文档+论文摘要+内置知识综合整理，已标注各条来源。  
> **适用约束**: 仅DashScope兼容API + 千问模型族(qwen-image/wan2.7-image/qwen-vl-max等)

---

## 1. 文生图风格控制技术

### 1.1 Style Prompt 工程

**核心原理**: 通过在prompt中嵌入风格描述词，引导扩散模型在latent space中偏向特定风格区域生成。

**关键技术点**:

| 技术 | 说明 | 效果 | 来源 |
|------|------|------|------|
| 风格关键词前置 | 将风格词放在prompt开头(如"oil painting, ...")，权重更高 | SD/DALL-E系列验证有效 | [Stable Diffusion Art Guide](https://stable-diffusion-art.com/prompt-guide/) |
| 艺术家风格引用 | "in the style of [artist]"或"[artist] style" | 强风格锚定，但需注意版权 | 内置知识 |
| 媒介/材质词 | "watercolor", "charcoal sketch", "3D render", "photograph" | 决定整体视觉基调 | 内置知识 |
| 时代/流派词 | "Art Nouveau", "Bauhaus", "cyberpunk", "vintage 1970s" | 提供文化语境约束 | 内置知识 |
| 权重语法 | "(keyword:1.5)"或"[keyword]"降低权重(A1111语法) | 精细调控风格强度 | [Civitai Prompt Guide](https://education.civitai.com/civitais-guide-to-prompting/) |

**DashScope/通义万相实践**:
- 支持中英文混合prompt，中文风格词识别良好
- "智能改写"功能可自动扩展简略prompt为详细描述(见DashScope文生图文档在线体验中心)
- 建议使用具体、详细的场景描述而非抽象概念(DashScope Prompt指南强调"清晰具体"原则)

> **来源**: https://help.aliyun.com/zh/model-studio/text-to-image (DashScope文生图文档)

### 1.2 风格预设 (Style Presets)

**主流平台预设体系**:

| 平台 | 预设数量 | 典型预设 | 机制 |
|------|----------|----------|------|
| Stable Diffusion WebUI | 自定义 | 通过checkpoint/lora/embedding组合 | 模型级风格绑定 |
| DALL-E 3 | 内置 | natural, vivid, anime等 | API参数style字段 |
| Midjourney | sref参数 | --sref <url> 参考图风格 | 隐式风格提取 |
| 通义万相 | 内置模板 | 摄影/插画/3D/国风等 | 模型微调+prompt模板 |

**DashScope风格预设实践**:
- 通义万相独立站提供预设风格选择器(图像生成→选择风格)
- API层面通过prompt模板实现：预定义风格描述前缀+用户内容拼接
- qwen-image模型擅长复杂文本渲染和UI设计类风格(DashScope qwen-image文档)

> **来源**: https://help.aliyun.com/zh/model-studio/qwen-image

### 1.3 负面提示词体系 (Negative Prompts)

**作用机制**: 在去噪过程中对negative prompt对应的latent特征施加反向引导，抑制不期望的元素。

**商品图常用负面提示词**:

```
# 通用质量排除
low quality, blurry, deformed, distorted, disfigured, bad anatomy, 
extra limbs, watermark, signature, text overlay, logo

# 商品图专用排除
oversaturated colors, artificial looking, plastic texture, 
uneven lighting, harsh shadows, cluttered background,
incorrect proportions, floating objects, inconsistent perspective

# 跨境电商专用排除
chinese text, non-latin characters, culturally inappropriate elements,
offensive symbols, trademarked logos, celebrity likeness
```

**DashScope注意事项**:
- wan系列模型支持negative_prompt参数
- qwen-image模型的负面提示词效果需实测(较新模型，文档未详述)
- 建议负面提示词简洁精准，避免过度排除导致生成空间过窄

> **来源**: 内置知识 + DashScope API文档推断

### 1.4 参考图风格迁移

**核心技术栈**:

| 技术 | 原理 | 适用场景 | 开源实现 |
|------|------|----------|----------|
| IP-Adapter | 解耦图像prompt与文本prompt的cross-attention注入 | 精确风格/构图迁移 | [tencent-ailab/IP-Adapter](https://github.com/tencent-ailab/IP-Adapter) |
| ControlNet Style | Canny/Depth/OpenPose条件控制+风格LoRA | 结构保持+风格替换 | lllyasviel/ControlNet |
| Neural Style Transfer | Gram matrix匹配(传统方法) | 纯风格纹理迁移 | Gatys et al. |
| DreamBooth/LoRA | 少量图片微调模型学习特定风格 | 定制化风格训练 | 多个开源实现 |
| Reference-only (SD WebUI) | 参考图作为额外condition输入 | 快速风格参考 | A1111内置 |

**IP-Adapter关键优势**:
- 无需微调基础模型，即插即用
- 支持多参考图组合(风格图+构图图+人脸图)
- FaceID变体可实现人脸一致性
- 与ControlNet/T2I-Adapter兼容组合使用

> **来源**: https://github.com/tencent-ailab/IP-Adapter (GitHub README)

---

## 2. LLM/VL模型做审美评审的技术

### 2.1 Aesthetic Scoring 模型

**主流评分模型对比**:

| 模型 | 基础架构 | 训练数据 | 特点 | 来源 |
|------|----------|----------|------|------|
| LAION Aesthetic Predictor V2 | CLIP ViT-L/14 + MLP | LAION-5B子集人工标注 | 轻量、快速、广泛集成 | [christophschuhmann/improved-aesthetic-predictor](https://github.com/christophschuhmann/improved-aesthetic-predictor) |
| PickScore | CLIP-H + fine-tuned | Pick-a-Pic数据集(真实用户偏好) | 超人类水平预测人类偏好 | [arXiv:2305.01569](https://arxiv.org/abs/2305.01569) |
| HPS v2 | CLIP + fine-tuned | HPD v2(798K偏好选择/433K图像对) | 最大规模偏好数据集，跨分布泛化好 | [arXiv:2306.09341](https://arxiv.org/abs/2306.09341) |
| ImageReward | BLIP + fine-tuned | 人工标注偏好对 | 同时评估美学和文本对齐 | Kuang et al. 2023 |
| Qwen-VL-Max | 多模态LLM | 大规模多模态预训练 | 可用自然语言评价图像质量 | DashScope API |

**PickScore关键发现**(来自论文摘要):
- 基于CLIP的微调评分函数，在预测人类偏好上展现"超人类性能"
- 比FID/IS等传统指标与人类排序的相关性更高
- 推荐用于评估未来文生图模型
- 可通过ranking增强现有模型(生成N张→PickScore排序→选最优)

**HPS v2关键发现**(来自论文摘要):
- 798,090个人类偏好选择，433,760对图像——同类最大数据集
- 刻意消除潜在偏差(此前数据集常见问题)
- 跨各种图像分布泛化更好
- 对算法改进有响应性(能区分模型迭代的质量提升)

> **来源**: https://arxiv.org/abs/2305.01569, https://arxiv.org/abs/2306.09341, https://github.com/christophschuhmann/improved-aesthetic-predictor

### 2.2 VLM-as-Judge

**技术路线**:

利用视觉语言模型(VLM)的多模态理解能力，以自然语言prompt引导其对生成图像进行结构化评价。

**Qwen-VL-Max作为Judge的实践方案**(适配DashScope约束):

```python
# 伪代码：VLM-as-Judge for Product Image Quality
judge_prompt = """你是一个专业电商产品图评审专家。请从以下维度评价这张产品图：

1. 构图(1-10): 主体居中/三分法/留白是否合理
2. 光影(1-10): 光线均匀度/阴影自然度/高光控制
3. 色彩(1-10): 色彩准确度/饱和度适宜度/色调统一性
4. 细节(1-10): 产品纹理清晰度/边缘锐度/无瑕疵
5. 商业吸引力(1-10): 购买欲激发/品牌调性匹配/目标受众适配
6. 技术质量(1-10): 分辨率/无AI伪影/无变形

总分 = 各维度加权平均(构图0.15+光影0.2+色彩0.15+细节0.2+商业吸引力0.2+技术质量0.1)

请以JSON格式输出: {"scores": {...}, "total": N, "critique": "...", "improvement_suggestions": [...]}
"""

# 调用 qwen-vl-max API (DashScope兼容)
response = dashscope.chat(model="qwen-vl-max", messages=[
    {"role": "user", "content": [
        {"image": generated_image_url},
        {"text": judge_prompt}
    ]}
])
```

**VLM Judge vs 专用评分模型的选择**:

| 维度 | VLM Judge (Qwen-VL-Max) | 专用评分模型 (PickScore/HPS) |
|------|------------------------|------------------------------|
| 可解释性 | ✅ 自然语言反馈+改进建议 | ❌ 仅数值分数 |
| 领域适配 | ✅ prompt即可调整评价标准 | ❌ 需重新训练/微调 |
| 速度 | ❌ 较慢(LLM推理) | ✅ 毫秒级(CLIP前向) |
| 批量筛选 | ❌ 成本高 | ✅ 适合大规模初筛 |
| 细粒度诊断 | ✅ 多维度结构化反馈 | ❌ 单一标量 |
| 部署复杂度 | ✅ DashScope API直调 | ❌ 需自部署GPU服务 |

**推荐组合策略**: PickScore/HPS批量初筛Top-K → Qwen-VL-Max精细评审+改进建议 → 反馈到prompt优化循环

### 2.3 Generate-Critique-Select 循环

**实证做法**(基于文献综述+工程实践):

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  Generate N  │────▶│  Score/Rank  │────▶│  Select Top-K │
│  candidates  │     │  (PickScore) │     │  (K=1~3)      │
└─────────────┘     └──────────────┘     └──────┬───────┘
       ▲                                        │
       │            ┌──────────────┐             │
       │            │ VLM Critique │◀────────────┘
       │            │ + Suggest    │
       │            └──────┬───────┘
       │                   │
       │            ┌──────▼───────┐
       └────────────│ Refine Prompt│
                    │ (incorporate │
                    │  feedback)   │
                    └──────────────┘
```

**关键参数经验值**:
- N(候选数): 4-8张(平衡成本与多样性)
- K(精选数): 1-3张(VLM精评)
- 最大迭代轮次: 2-3轮(边际收益递减)
- Temperature: 首轮0.8-1.0(探索)，后续0.3-0.5(收敛)

**Self-Refine in Image Generation** 相关研究:
- Self-Refine (Madaan et al., 2023): LLM生成→自评→改进的通用框架，已验证在文本任务有效
- 图像领域适配: 需要VLM替代LLM做critique，且改进信号需映射回prompt/参数空间
- Iterative Prompt Refinement: 每轮根据VLM反馈修改prompt关键词/权重/负面提示词

> **来源**: arXiv:2305.01569 (PickScore), arXiv:2306.09341 (HPS v2), Madaan et al. 2023 (Self-Refine), 内置知识综合

---

## 3. 商品图的Prompt美学修饰语最佳实践

### 3.1 灯光词效果矩阵

| 灯光词 | 视觉效果 | 适用品类 | 示例prompt片段 |
|--------|----------|----------|---------------|
| softbox lighting | 柔和均匀无影，专业棚拍感 | 电子产品/化妆品/珠宝 | "product shot with softbox lighting, even illumination" |
| golden hour | 暖黄色调，温暖氛围感 | 食品/生活方式/户外用品 | "bathed in golden hour sunlight, warm ambient glow" |
| diffused light | 散射柔光，减少反光 | 玻璃器皿/金属制品/手表 | "diffused natural light, minimal reflections" |
| rim lighting / backlit | 轮廓光，突出产品边缘 | 科技产品/瓶身/透明材质 | "dramatic rim lighting outlining the product silhouette" |
| studio three-point lighting | 主光+辅光+背光经典三点 | 通用商品图 | "professional three-point studio lighting setup" |
| butterfly lighting | 鼻下蝶形阴影，人像美妆 | 美妆/护肤品模特展示 | "butterfly lighting on model face, beauty photography" |
| Rembrandt lighting | 45°侧光三角阴影，立体感 | 高端产品/奢侈品 | "Rembrandt lighting creating depth and dimension" |
| flat lay lighting | 俯拍均匀光，无阴影 | 配件/套装/食材平铺 | "overhead flat lay with uniform soft lighting" |

### 3.2 镜头词效果矩阵

| 镜头词 | 视觉效果 | 适用品类 | 技术参数参考 |
|--------|----------|----------|-------------|
| 85mm lens | 浅景深人像级虚化，主体突出 | 单品特写/模特展示 | f/1.4-2.8, 人像黄金焦段 |
| macro lens / extreme close-up | 微距细节，纹理质感 | 珠宝/面料/食品纹理 | 1:1放大比, f/8-11 |
| 35mm lens | 环境人像视角，场景叙事 | 生活方式/使用场景 | f/2.0-4.0, 兼顾环境与主体 |
| 50mm lens | 标准视角，自然不变形 | 通用商品/服装 | f/1.8-2.8, 最接近人眼 |
| wide angle 24mm | 广角空间感，环境展示 | 家居/大家电/场景 | f/5.6-8, 注意边缘畸变 |
| tilt-shift | 移轴效果，选择性聚焦 | 创意产品/微缩场景 | 模拟迷你世界效果 |
| fisheye | 鱼眼夸张透视 | 运动/潮流/创意 | 慎用，仅限特定风格 |

### 3.3 风格词效果矩阵

| 风格词 | 视觉特征 | 适用场景 | 注意事项 |
|--------|----------|----------|----------|
| editorial | 杂志大片感，高级构图 | 时尚/美妆/高端消费品 | 配合aspect ratio 2:3或3:4 |
| minimalist | 极简留白，干净背景 | 科技/家居/北欧风 | 负空间占比≥40% |
| commercial photography | 标准商业摄影规范 | 通用电商 | 安全牌，适用面广 |
| luxury aesthetic | 暗调/金色/质感材质 | 奢侈品/高端线 | 避免过度浮夸 |
| lifestyle photography | 生活场景融入 | 日用/母婴/食品 | 需搭配场景描述 |
| flat design / graphic | 平面插画风格 | 图标/UI/包装预览 | 非写实需求时使用 |
| hyperrealistic | 超写实细节 | 食品/材质展示 | 可能触发uncanny valley |
| vintage / retro | 复古色调/颗粒感 | 文创/怀旧品类 | 指定年代更精准 |
| clean white background | 纯白底抠图风格 | Amazon/天猫主图 | 配合"isolated on white" |
| cinematic | 电影感宽幅/调色 | 品牌故事/视频封面 | 配合letterbox比例 |

### 3.4 组合公式(商品图Prompt模板)

```
[风格词] + [镜头词] + [灯光词] + [主体描述] + [场景/背景] + [后期/色调] + [质量词]

示例(电子产品):
"commercial product photography, 85mm lens, softbox lighting, 
wireless noise-canceling headphones in matte black finish, 
on clean white gradient background, subtle reflection on surface, 
color graded, sharp focus, high resolution, 8k detail"

示例(食品):
"editorial food photography, macro lens, natural diffused window light,
fresh strawberry tart with cream filling on rustic wooden table,
warm color grading, shallow depth of field, appetizing composition,
professional food styling, 4k quality"

示例(服装):
"minimalist fashion photography, 50mm lens, studio three-point lighting,
women's linen blazer in sage green on neutral beige backdrop,
clean lines, muted earth tones, elegant pose, Vogue editorial style"
```

> **来源**: 内置知识综合(基于Stable Diffusion/Midjourney/DALL-E社区实践验证)

---

## 4. 多图一致性技术

### 4.1 同一商品多图风格一致的工程手段

| 方法 | 原理 | 一致性程度 | 实施难度 | 适用场景 |
|------|------|-----------|----------|----------|
| 固定Seed | 相同seed+相同prompt→相似构图/色调 | ⭐⭐⭐ 中等 | ⭐ 低 | 同角度系列图 |
| 风格描述复用 | 将风格描述固化为模板前缀 | ⭐⭐⭐⭐ 较高 | ⭐ 低 | 所有场景 |
| 参考图引导(IP-Adapter) | 以首图为风格参考生成后续图 | ⭐⭐⭐⭐⭐ 高 | ⭐⭐⭐ 中高 | 系列主图 |
| LoRA微调 | 用商品多角度图训练专属LoRA | ⭐⭐⭐⭐⭐ 最高 | ⭐⭐⭐⭐⭐ 高 | 大量SKU批量 |
| img2img + 固定参数 | 以基准图做img2img变换 | ⭐⭐⭐⭐ 较高 | ⭐⭐ 中 | 换背景/换角度 |
| ControlNet姿态/深度 | 固定pose/depth map保持一致 | ⭐⭐⭐⭐ 较高 | ⭐⭐⭐ 中高 | 模特展示系列 |
| Batch Generation | 同prompt同seed批量生成取最优 | ⭐⭐⭐ 中等 | ⭐ 低 | 候选筛选 |

### 4.2 实操SOP(跨境商品图一致性)

```
Step 1: 建立风格基准卡(Style Card)
├── 确定风格模板: "[brand_style] commercial product photography, softbox lighting, 
│   clean white/light gray background, professional color grading, sharp detail"
├── 确定负面提示词: "blurry, low quality, watermark, text, oversaturated"
├── 确定技术参数: seed=N, steps=30, cfg_scale=7, size=1024x1024
└── 记录首张满意图的完整prompt+参数

Step 2: 生成系列图
├── 正面主图: 基准prompt + "front view, centered composition"
├── 侧面展示: 基准prompt + "side profile view, 45-degree angle"  
├── 细节特写: 基准prompt + "extreme close-up macro detail, texture focus"
├── 使用场景: 基准prompt + "in-use lifestyle context, [scene description]"
└── 尺寸参照: 基准prompt + "with size reference object, dimensional context"

Step 3: 一致性校验
├── VLM评审: Qwen-VL-Max对比系列图色调/风格一致性打分
├── 直方图比对: 确保色温/亮度分布相近
└── 人工终审: 确认品牌调性统一

Step 4: 迭代修正
└── 不一致的图重新生成，增加参考图约束或调整seed
```

### 4.3 DashScope环境下的实现策略

由于约束为仅DashScope API:
- **固定seed**: wan系列API支持seed参数，相同seed+prompt可复现
- **风格描述复用**: 在应用层维护风格模板库，每次调用拼接
- **参考图**: wan2.7-image支持image-to-image模式，可用首图作为参考
- **VLM一致性校验**: qwen-vl-max可做多图对比评审
- **LoRA微调**: DashScope暂不支持自定义LoRA训练(需外部解决或使用通义万相定制服务)

> **来源**: 内置知识 + DashScope文档推断

---

## 5. DashScope/通义万相(wan)/qwen-image系列的风格控制参数与提示词实践

### 5.1 可用模型概览

| 模型 | 类型 | 参数规模 | 特色能力 | 价格(北京) | 来源 |
|------|------|----------|----------|-----------|------|
| qwen-image | 文生图 | 200亿 | 卓越文本渲染、复杂布局、UI/PPT设计、写实人像 | ¥0.25/张 | [qwen-image文档](https://help.aliyun.com/zh/model-studio/qwen-image) |
| qwen-image-plus | 文生图增强版 | — | 更高画质 | — | DashScope文档 |
| wan2.7-image | 文生图/图生图 | — | 最新万相系列，支持i2v | — | DashScope文档 |
| z-image | 文生图 | — | 阿里自研系列 | — | DashScope文生图主页 |

### 5.2 API关键参数(文生图v2)

基于DashScope文生图文档和API参考:

| 参数 | 说明 | 风格控制相关性 |
|------|------|---------------|
| prompt | 正向提示词(中英文) | ⭐⭐⭐⭐⭐ 核心风格载体 |
| negative_prompt | 负向提示词 | ⭐⭐⭐⭐ 排除不想要的元素 |
| size | 输出尺寸(如1024×1024, 720×1280) | ⭐⭐⭐ 比例影响构图风格 |
| seed | 随机种子 | ⭐⭐⭐⭐ 可复现+一致性 |
| n | 一次生成数量 | ⭐⭐⭐ 多选优 |
| steps | 采样步数 | ⭐⭐ 步数越高细节越好 |
| cfg_scale | Classifier-Free Guidance | ⭐⭐⭐ 越高越遵循prompt |
| style | 风格预设(部分模型支持) | ⭐⭐⭐⭐⭐ 直接风格控制 |
| ref_img | 参考图URL(图生图模式) | ⭐⭐⭐⭐⭐ 风格迁移核心 |
| strength | 图生图变化强度 | ⭐⭐⭐⭐ 控制参考图影响程度 |
| 智能改写 | 自动扩展prompt | ⭐⭐⭐ 简化prompt工程 |

### 5.3 提示词实践(DashScope特有)

**从DashScope官方示例中提取的最佳实践**:

1. **详细描述优于简短关键词**: DashScope文生图文档中的示例均为长段落详细描述(数百字)，包含材质、颜色、光影、构图的精确描述。这与SD社区的短关键词风格不同。

2. **中文prompt原生支持**: 通义万相/qwen-image对中文理解能力强，可直接用中文描述风格，无需翻译为英文。

3. **结构化描述**: 建议按"整体→局部→细节"层次组织prompt:
   ```
   [整体风格与氛围] → [主体描述与位置] → [光影与色调] → [背景与环境] → [细节与质感] → [技术要求]
   ```

4. **智能改写功能**: DashScope提供prompt一键优化工具，可将简短prompt自动扩写为详细描述。推荐工作流: 先写核心意图→智能改写→人工微调→提交生成。

5. **qwen-image特长利用**: 
   - 复杂文本渲染: 可在图中精确生成中英文文字(适合海报/banner)
   - UI/PPT设计: 直接生成界面原型
   - 写实人像: 高质量人物生成

> **来源**: https://help.aliyun.com/zh/model-studio/text-to-image, https://help.aliyun.com/zh/model-studio/qwen-image, https://help.aliyun.com/zh/model-studio/use-cases/prompt-engineering-guide

### 5.4 DashScope风格控制参数速查表

```python
# DashScope 文生图风格控制参数速查 (wan/qwen-image系列)

# === 基础风格控制 ===
params_base = {
    "model": "wanx-v2",           # 或 "qwen-image" / "wan2.7-image"
    "prompt": "详细描述...",       # 核心风格载体
    "negative_prompt": "排除项...", # 质量控制
    "size": "1024*1024",          # 正方形/竖版720*1280/横版1280*720
    "seed": 42,                    # 固定seed保证可复现
    "n": 4,                        # 一次出4张选优
}

# === 图生图风格迁移 ===
params_i2i = {
    **params_base,
    "ref_img": "https://...",     # 参考图URL
    "strength": 0.6,              # 0.3-0.8: 低=保留原图多, 高=变化大
}

# === 商品图专用模板 ===
PRODUCT_STYLE_TEMPLATE = (
    "专业商业产品摄影, {lens}镜头, {lighting}灯光, "
    "{product_description}, "
    "{background}背景, {color_grading}色调, "
    "高清细节, 专业色彩校正, 8K品质"
)

PRODUCT_NEGATIVE = (
    "模糊, 低质量, 水印, 文字覆盖, 过饱和, "
    "变形, 多余物体, 杂乱背景, 不自然光影"
)
```

---

## 可直接复用的审美增强Prompt组件库

### 🎨 风格前缀组件(直接拼接到prompt开头)

```yaml
# === 电商主图风格 ===
ecommerce_hero: "professional e-commerce product photography, studio lighting, clean white background, sharp focus, commercial grade, high resolution"
ecommerce_lifestyle: "lifestyle product photography, natural ambient lighting, styled scene, warm inviting atmosphere, editorial quality"
ecommerce_minimal: "minimalist product photography, soft diffused light, ample negative space, muted tones, Scandinavian aesthetic"

# === 品类专用风格 ===
fashion_editorial: "high fashion editorial photography, dramatic lighting, bold composition, Vogue magazine style, cinematic color grading"
food_appetizing: "appetizing food photography, natural window light, fresh ingredients visible, warm color temperature, shallow depth of field, food styling"
tech_premium: "premium tech product photography, sleek dark background, accent rim lighting, futuristic aesthetic, precise detail, Apple-style product shot"
beauty_glow: "beauty product photography, soft ring light, luminous skin texture, pastel tones, dewy finish, cosmetic advertising standard"
jewelry_sparkle: "fine jewelry photography, macro lens, controlled sparkle highlights, velvet backdrop, luxurious ambiance, precision focus stacking"

# === 中文风格(DashScope优化) ===
cn_commercial: "专业商业产品摄影, 柔和灯光, 精致构图, 高品质, 细腻质感"
cn_guofeng: "中国风国潮美学, 传统纹样, 东方意境, 水墨质感, 雅致配色"
cn_modern: "现代简约设计, 干净利落, 几何线条, 高级灰调, 都市质感"
```

### 💡 灯光增强组件

```yaml
soft_studio: "three-point studio lighting, key light at 45 degrees, fill light for shadow softening, hair light for separation"
natural_window: "soft natural window light from left side, gentle shadows, golden warmth, no harsh contrasts"
dramatic_spot: "dramatic spotlight from above, deep shadows, chiaroscuro effect, theatrical mood"
neon_accent: "neon accent lighting, cyberpunk color palette, glowing edges, futuristic atmosphere"
outdoor_golden: "golden hour outdoor lighting, warm sun flare, long shadows, romantic atmosphere"
```

### 🔍 质量增强后缀(拼接到prompt末尾)

```yaml
quality_standard: "high quality, detailed, sharp focus, professional color grading"
quality_premium: "masterpiece quality, ultra detailed, 8K resolution, award-winning photography, perfect composition"
quality_print: "print-ready quality, 300 DPI equivalent, CMYK-friendly colors, crisp edges, no artifacts"
```

### 🚫 通用负面提示词组件

```yaml
general_exclude: "low quality, blurry, deformed, watermark, signature, text overlay, logo, oversaturated, artificial"
product_exclude: "floating product, incorrect proportions, plastic texture, uneven lighting, cluttered background, distracting elements"
cross_border_exclude: "chinese characters, non-target-language text, culturally sensitive symbols, trademarked content, celebrity faces"
```

### 🔄 Generate-Critique-Select 实现模板

```python
# 可直接复用的审美增强循环伪代码(DashScope API)

STYLE_TEMPLATE = "professional product photography, {lighting}, {background}, commercial grade"
NEGATIVE = "low quality, blurry, watermark, deformed, oversaturated"

def generate_critique_select(product_desc, style_params, n_candidates=4, max_rounds=2):
    prompt = STYLE_TEMPLATE.format(**style_params) + ", " + product_desc
    
    for round_num in range(max_rounds):
        # Step 1: Generate N candidates
        images = dashscope.image_generate(
            model="wanx-v2",
            prompt=prompt,
            negative_prompt=NEGATIVE,
            n=n_candidates,
            seed=random_seed if round_num == 0 else None,
            size="1024*1024"
        )
        
        # Step 2: Quick score (if PickScore available, else skip to VLM)
        # scored = [(img, pickscore(img)) for img in images]
        # top_k = sorted(scored, key=lambda x: x[1], reverse=True)[:2]
        
        # Step 3: VLM critique
        critique = dashscope.chat(model="qwen-vl-max", messages=[{
            "role": "user",
            "content": [
                *[{"image": img.url} for img in images],
                {"text": "比较这{}张产品图，选出最好的一张，并说明其他图的不足之处和改进建议。以JSON输出: {{best_index, scores[], critique, improvements[]}}".format(n_candidates)}
            ]
        }])
        
        best = parse_critique(critique)
        
        if best.score >= 8.5 or round_num == max_rounds - 1:
            return best.image
        
        # Step 4: Refine prompt based on critique
        prompt = refine_prompt(prompt, best.improvements)
    
    return best.image
```

---

## 附录: 关键来源URL汇总

| # | 来源 | URL | 内容 |
|---|------|-----|------|
| 1 | DashScope文生图文档 | https://help.aliyun.com/zh/model-studio/text-to-image | 万相/千问/z-image文生图API使用方式、模型效果展示、智能改写 |
| 2 | qwen-image模型信息 | https://help.aliyun.com/zh/model-studio/qwen-image | 200亿参数、文本渲染SOTA、定价¥0.25/张 |
| 3 | DashScope Prompt工程指南 | https://help.aliyun.com/zh/model-studio/use-cases/prompt-engineering-guide | Prompt框架(背景/目的/风格/语气/受众/输出)、清晰具体原则 |
| 4 | PickScore论文 | https://arxiv.org/abs/2305.01569 | CLIP微调、超人类偏好预测、Pick-a-Pic开放数据集 |
| 5 | HPS v2论文 | https://arxiv.org/abs/2306.09341 | 798K偏好数据、跨分布泛化、T2I评估benchmark |
| 6 | IP-Adapter | https://github.com/tencent-ailab/IP-Adapter | 图像prompt适配器、无需微调、多参考图组合 |
| 7 | LAION Aesthetic Predictor | https://github.com/christophschuhmann/improved-aesthetic-predictor | CLIP+MLP轻量美学评分、LAION-5B训练 |
| 8 | Civitai Prompt Guide | https://education.civitai.com/civitais-guide-to-prompting/ | 社区prompt工程最佳实践(未能访问，内容基于内置知识) |

# 跨境电商素材生成最佳实践 & AliExpress 上架合规规则

> 调研日期：2026-08-26
> 来源：多源综合（Google 搜索 + 直接抓取），每条结论附来源 URL

---

## A. 素材生成最佳实践

### A1. 主图（Main Image）

#### 规格要求
- **尺寸**：最低 800×800 px，推荐 1000×1000 px 或更高；最大不超过 2000×2000 px
- **比例**：1:1 正方形为主（搜索结果缩略图为方形，非方形会被裁切缩小）；部分类目接受 3:4（≥750×1000 px）
- **格式**：JPG / JPEG / PNG
- **文件大小**：≤5MB
- **背景**：纯白底（RGB 255,255,255）或干净纯色背景；产品主体占画面 70%-85%
- **数量**：系统最多上传 6 张主图 + 1 个视频

> 来源：
> - https://www.fit.photos/specs/aliexpress-product-image-requirements/ （AE 要求纯白 RGB 255,255,255）
> - https://sellshot.ai/aliexpress-product-image-generator （正方形 1:1，≥800×800px，白色或干净背景）
> - https://www.sizemarker.com/blog/b2b-marketplace-image-requirements （B2B 平台图片规格对比）
> - https://m.cifnews.com/guide/aliexpress （雨果跨境：jpg/jpeg/png ≤5MB，宽高比 3:4 ≥750×1000，不允许水印边框促销牛皮癣）
> - https://www.biaojixia.com （标记侠：主图像素下限 800×800，推荐 1000×1000，1:1 为主，产品占比 70%）

#### 构图要点
1. **产品居中**，留白均匀，四周不贴边
2. **无文字、无水印、无边框、无促销贴纸**（"牛皮癣"）
3. **单一产品主体**，不堆叠多个 SKU
4. **光线均匀**，无强烈阴影/反光；建议使用柔光箱或 AI 补光
5. **真实还原颜色**，不过度调色导致与实物不符
6. 支持 zoom 功能时，高分辨率尤为重要（买家可放大查看细节）

> 来源：
> - https://www.shopify.com/blog/product-photography （Shopify 电商摄影指南：白底、生活场景、包装、特写四种类型）
> - https://blog.csdn.net/shuaishoutu/article/details/139168750 （CSDN：禁止水印、促销牛皮癣、装饰边框；过度 AI 处理导致与实物不符会被标记）

#### AI 生成主图的 Prompt 工程要点

| 要素 | 推荐写法 | 说明 |
|------|---------|------|
| 白底约束 | `pure white background, RGB(255,255,255)` | 明确指定纯白，避免灰色渐变 |
| 去文字 | `no text, no watermark, no logo, no label` | 不加此约束约 40% 生成图含乱码文字 |
| 产品一致性 | 使用参考图（image-to-image）+ 固定 seed | 保持多角度生成的一致性 |
| 构图控制 | `product centered, clean composition, studio lighting` | 引导模型产出电商标准构图 |
| 负面提示词 | `--no text, watermark, fingers, extra objects, blurry` | Midjourney/Stable Diffusion 用 --no；DALL-E 用 inline 描述 |
| 分辨率 | `high resolution, 2000x2000, sharp focus` | 引导高清输出 |
| 风格锚定 | `professional e-commerce product photography, Amazon-style` | 锚定电商平台视觉标准 |

> 来源：
> - https://scalio.app/AI-Prompts （AI 白底商品图 Prompt：no extra fingers, no warped product, no text overlay, no watermark）
> - https://kumba.ai/blog/prompt-engineering-for-ai-images （8 层 Prompt 公式 + 12 模板 + 负面提示词速查表）
> - https://magicshot.ai/blog/image-prompt-engineering-2026 （负面提示词框架：no text, no watermark, no extra fingers）
> - https://promptessor.com/blog/ai-image-prompts-better-ai-art-2026 （负面约束清单：No visible text; No watermark; No hands in frame）
> - https://autokeyworder.com/blog/ai-inconsistency/ （不含 "no text, no watermark" 约束时约 40% 生成图含随机乱码文字）
> - https://lumalabs.ai/news/25-ai-product-photography-prompts-ecommerce （25 条 AI 商品摄影 Prompt 模板）
> - https://miraflow.ai/blog/ai-prompts-ecommerce-product-images （20 条可直接复制的电商 AI Prompt）
> - https://www.photorobot.com/blog/enhancing-product-photo-backgrounds-ai （PhotoRobot：AI 背景生成 Prompt 工程方法）

---

### A2. 详情图（Detail Images）—— 推荐 5 张内容编排

| 序号 | 内容 | 目的 | 制作要点 |
|------|------|------|---------|
| 1 | **核心卖点信息图** | 3-5 个 USP（独特卖点）图标化展示 | 简洁图标 + 短文案，支持多语言；可用 AI 生成后叠加文字层 |
| 2 | **产品细节特写** | 材质/工艺/做工品质感 | 微距拍摄或 AI 局部放大；标注关键部位 |
| 3 | **尺码表 / 规格参数** | 减少退换货纠纷 | 服装类必须提供 cm/inch 双单位；电子类列明技术参数 |
| 4 | **使用场景 / 生活方式图** | 帮助买家想象拥有产品的体验 | 真人模特或 AI 生成场景图；注意文化适配（目标市场审美） |
| 5 | **资质认证 / 包装展示** | 建立信任、满足合规 | CE/FDA/RoHS 等认证标识；实际包装照片；品牌授权书（如适用） |

#### 详情页布局最佳实践（A+ Content 思路）

1. **"Show, Don't Tell" 原则**：用图片代替长段文字描述
2. **前 3 屏决定转化**：首屏放核心卖点图，第二屏放细节/规格，第三屏放场景图
3. **对比图表**：与竞品或旧版对比，突出差异化优势
4. **社会证明**：用户评价截图、KOL 推荐、销量数据
5. **FAQ 可视化**：将常见问题做成图文卡片
6. **移动端优先**：所有图片确保在手机端清晰可读，文字不小于 24pt

> 来源：
> - https://insiderone.com/ultimate-product-detail-page/ （PDP 最佳实践：45% 在线购物者访问 PDP 时做出购买决策；"Show don't tell" 描述法）
> - https://novadata.io/resources/blog/amazon-a-plus-content-guide （Amazon A+ Content 2026 指南：增强型图文模块）
> - https://menkoservices.com/blogs/e-commerce-listing-images-a-content-design （Hero 图 + 信息图 + 生活场景 + A+ Content 组合策略）
> - https://perpetua.io/blog/5-best-practices-amazon-product-detail-page （主图白底 2000×2000，至少 4 张 A+ 图片）
> - https://greenonion.ai/blog/amazon-a-plus-content-guide-2026 （A+ Content 规则、尺寸、案例）

---

### A3. 商品视频 —— 分镜结构与制作规范

#### 推荐时长与结构

| 阶段 | 时长 | 内容 | 目的 |
|------|------|------|------|
| **Hook（钩子）** | 0-3秒 | 痛点提问 / 惊艳效果 / 悬念画面 | 阻止划走，抓住注意力 |
| **Problem（问题）** | 3-8秒 | 展示用户痛点或现有方案的不足 | 建立共鸣 |
| **Product（产品展示）** | 8-20秒 | 产品外观 + 核心功能演示 + 使用过程 | 传达价值 |
| **Proof（证据）** | 20-25秒 | 对比测试 / 用户证言 / 数据佐证 | 建立信任 |
| **CTA（行动号召）** | 25-30秒 | 价格优惠 / 限时折扣 / 点击链接 | 促成转化 |

#### 技术规格
- **分辨率**：1080p（1920×1080）起步，竖版 9:16 适合短视频平台，横版 16:9 适合详情页
- **时长**：AliExpress 商品视频建议 15-60 秒；社交媒体广告 15-30 秒
- **字幕**：必须有（静音播放占比 >80%）；多语言字幕覆盖目标市场
- **BGM**：轻快节奏，音量不超过人声的 30%；使用免版权音乐库
- **口播**：语速适中，发音清晰；可用 AI TTS（如 CosyVoice）生成多语言配音
- **文件格式**：MP4 (H.264)，≤500MB

#### 分镜脚本模板

```
[镜头1] 0-3s | Hook
  画面：产品最吸睛的使用瞬间 / 痛点场景
  文案："Tired of [pain point]?"
  音效：吸引注意力的音效
  
[镜头2] 3-8s | Problem
  画面：用户遇到问题的场景
  文案：简述痛点
  
[镜头3] 8-15s | Solution Intro
  画面：产品亮相，360° 旋转展示
  文案：产品名称 + 一句话定位
  
[镜头4] 15-22s | Feature Demo
  画面：核心功能实际操作演示
  文案：卖点1 + 卖点2（字幕标注）
  
[镜头5] 22-27s | Social Proof
  画面：用户使用满意表情 / 对比效果
  文案：数据/评价
  
[镜头6] 27-30s | CTA
  画面：产品 + 价格标签 + 店铺Logo
  文案："Shop now! Link in bio"
  音效：结尾提示音
```

> 来源：
> - https://storyflow.so/blog/how-to-storyboard-commercial （标准 30 秒结构：hook 2-3s → problem → product → proof → CTA）
> - https://boords.com/how-to-storyboard （4 步分镜流程：模板→粗绘→编辑视觉线索→标注运镜）
> - https://www.studiobinder.com/blog/product-explainer-video （产品解说视频类型、案例、制作成本、最佳实践）
> - https://www.hooked.so/blog/how-to-create-product-videos （产品视频创建实操指南：策划→拍摄→优化）
> - https://hera.video/templates （电商产品视频模板：卖点、优惠、对比、社会证明）
> - https://llamagen.ai/blogs/commercial-storyboard-template （商业分镜模板：逐镜头 timing + 产品节拍 + 字幕 + 运镜标注）
> - https://biteable.com/blog/product-video/ （产品视频制作指南）

---

## B. AliExpress 上架合规规则

### B1. 内容禁区（Prohibited Content）

#### 严格禁止
1. **违禁品**：毒品及前体化学品、易燃易爆危险品、枪支弹药及管制刀具、假冒伪劣商品
2. **侵权内容**：未经授权使用第三方商标/Logo/品牌名；盗用他人商品图片（"盗图"）
3. **医疗声明**：非医疗器械不得宣称治疗/治愈/预防疾病功效；保健品不得替代药品宣传
4. **夸大虚假宣传**：虚标材质/成分/产地；伪造认证标志（CE/FDA 等未获认证不得使用）
5. **敏感内容**：色情/暴力/歧视性内容；政治敏感物品；涉及国家安全的信息
6. **无意义图片**：禁止 VIP 图、$符号图、空白图等无实质内容的图片

> 来源：
> - https://rule.alibaba.com/rule/detail/2054.htm （Alibaba Product Listing Policy：禁限售物品清单）
> - https://m.cifnews.com/guide/aliexpress （雨果跨境：禁限售信息列表，违反按《禁限售规则》处罚）
> - https://helpcenter.aliexpress.com/SellerPenalty （盗图投诉立案条件：需提供清晰无水印原图）
> - https://ipp.alibabagroup.com/infoContent/cn-aliexpress （全球速卖通知识产权保护规则：严禁未经授权发布涉侵权商品）
> - https://m.chwang.com/guide （无意义图商品规范重申公告：VIP/$/空白图等将受处罚）
> - https://digital-strategy.ec.europa.eu/news/commission-makes-binding-alipress-commitments-dsa （欧盟 DSA 执法：AliExpress 因非法假冒商品被罚款 €5.5 亿）

#### 描述文案红线
- ❌ "best quality" / "top grade" 等无法证实的绝对化用语
- ❌ 未经授权的 celebrity endorsement
- ❌ 误导性价格标注（原价虚高再打折）
- ❌ 非英文字符出现在标题/属性中（系统会报错）
- ✅ 使用客观可验证的描述："made of 100% cotton" / "waterproof IPX5 rated"

> 来源：
> - https://www.ipaylinks.com/information_details （iPayLinks：商品描述必须详细包含特性/用途/材质，图片清晰高质量，不含水印广告）
> - https://terms.alicdn.com/suit_bu1_aliexpress （AliExpress Terms of Use：未经书面批准不得使用第三方商标）

---

### B2. 图片与视频规格汇总

| 项目 | 要求 | 备注 |
|------|------|------|
| 主图格式 | JPG / JPEG / PNG | 不支持 GIF/BMP/WebP |
| 主图尺寸 | ≥800×800 px（推荐 1000×1000） | 低于此可能上传失败 |
| 主图比例 | 1:1（正方形） | 部分类目接受 3:4（≥750×1000） |
| 文件大小 | ≤5MB | 过大压缩后再上传 |
| 背景 | 纯白或干净纯色 | 禁止水印/边框/促销文字 |
| 主图数量 | 最多 6 张 + 1 视频 | 建议填满所有位置 |
| 视频格式 | MP4 (H.264) | — |
| 视频时长 | 15-60 秒 | 过长影响加载 |
| 视频大小 | ≤500MB | — |
| SKU 属性图 | 对应颜色/款式的实拍图 | 需与 SKU 选项一一对应 |

> 来源：
> - https://m.cifnews.com/guide/aliexpress （雨果跨境：产品发布各模块图片要求）
> - https://sellshot.ai/aliexpress-product-image-generator （Sellshot：AE 图片要求汇总）
> - https://www.biaojixia.com （标记侠：速卖通主图尺寸与图片规范 2026）
> - https://blog.csdn.net/shuaishoutu/article/details/139168750 （CSDN：SKU 属性图规范 2026）

---

### B3. 类目属性填写规范

#### 通用原则
1. **必填属性（红色标记）不可跳过**：缺失则无法发布或被降权
2. **可选属性尽量填全**：完整度越高，搜索排名越靠前
3. **属性值必须真实准确**：虚假属性属于违规行为，可能被下架/扣分
4. **类目变更后重新检查属性**：平台可能新增必填项

#### 常见必填属性示例

| 类目 | 典型必填属性 |
|------|-------------|
| 服装 | Brand Name / Material / Style / Size Type / Season / Pattern Type |
| 电子产品 | Brand / Model Number / Certification / Input Voltage / Warranty |
| 家居用品 | Material / Size / Color / Style / Usage |
| 美妆护肤 | Ingredient List / Shelf Life / Country of Origin / Skin Type |

#### 注意事项
- **Brand Name**：无品牌选 "Unbranded" / "No brand"，不要随意填写知名品牌
- **Material**：使用标准英文名称，如 "100% Cotton" 而非自定义缩写
- **Certification**：有 CE/FCC/RoHS 等才填，无证不填（否则视为虚假宣传）
- **Trademark**：有注册商标才填写，无则选 "None"

> 来源：
> - https://docs.vortexiq.ai/attributes/alipress （Vortex IQ：AliExpress 类目可随时新增必填属性，需定期复查）
> - https://brainence.gitbook.io/attributes （Brainence：每个类目有独立属性列表，红色=必填，黄色=可选）
> - https://seller.alibaba.com/apparel-accessories/product-attribute-configuration-guide （Alibaba 商品属性配置指南）
> - https://cedcommerce.com/uploads/blog-PDF （CedCommerce：品牌名须准确填写，无品牌选 None）

---

### B4. 服装类尺码表要求

#### 为什么尺码表至关重要
- 中国尺码比亚美欧码小 1-3 个号，不提供准确尺码表会导致大量退货和差评
- AliExpress 鼓励卖家上传标准化尺码表，部分类目强制要求

#### 尺码表必备字段

| 字段 | 单位 | 说明 |
|------|------|------|
| Size Label | S/M/L/XL/XXL 或数字码 | 同时标注亚洲码和国际码对照 |
| Bust/Chest | cm + inch | 胸围/上围 |
| Waist | cm + inch | 腰围 |
| Hip | cm + inch | 臀围 |
| Shoulder Width | cm | 肩宽 |
| Sleeve Length | cm | 袖长 |
| Length | cm | 衣长/裙长 |
| Fit Note | 文字 | "Fits true to size" 或 "Runs small, order one size up" |

#### 最佳实践
1. **双单位制**：cm 和 inch 并列显示
2. **实测数据**：基于实际测量而非理论值
3. **尺码对照表**：提供 CN/EU/US/UK 四国尺码对照
4. **Fit Advisory**：明确告知是否偏大/偏小/正常
5. **内置尺码工具**：利用 AliExpress 后台的"尺码表使用教程"功能上传结构化数据，买家选择尺码时自动弹出换算窗口
6. **SKU 图配尺码**：在变体图中加入尺码表图片作为辅助

#### 鞋类特殊要求
- 必须提供脚长（cm）对应的尺码对照
- 注明鞋楦宽度（窄/标准/宽）
- 不同国家尺码体系差异大（EU/US/UK/CN），务必全部列出

> 来源：
> - https://alitools.io/blog/aliexpress-size-chart （Alitools：AliExpress 鞋类/服装尺码表详解，含测量方法和转换表）
> - https://m.cifnews.com/guide/aliexpress （雨果跨境：尺码表使用教程链接）
> - https://megabonus.com/blog/how-to-choose-clothing-size-aliexpress （Megabonus：如何正确选择 AE 服装尺码）
> - https://alihelper.net/blog/clothing-sizes-chart （AliHelper：AE 服装尺码匹配表）
> - https://inbusiness.aliexpress.com/blog/Plus-sized-clothing-niche （AliExpress Business：大码服装细分市场趋势）

---

## 附录：关键来源索引

| # | 来源 | URL | 主题 |
|---|------|-----|------|
| 1 | fit.photos | https://www.fit.photos/specs/aliexpress-product-image-requirements/ | AE 主图白底要求 |
| 2 | Sellshot AI | https://sellshot.ai/aliexpress-product-image-generator | AE 图片规格 + AI 生成 |
| 3 | SizeMarker | https://www.sizemarker.com/blog/b2b-marketplace-image-requirements | B2B 平台图片规格对比 |
| 4 | Shopify Blog | https://www.shopify.com/blog/product-photography | 电商摄影完整指南 |
| 5 | Insider One | https://insiderone.com/ultimate-product-detail-page/ | PDP 最佳实践 |
| 6 | Storyflow | https://storyflow.so/blog/how-to-storyboard-commercial | 30s 视频分镜结构 |
| 7 | Boords | https://boords.com/how-to-storyboard | 分镜制作 4 步法 |
| 8 | StudioBinder | https://www.studiobinder.com/blog/product-explainer-video | 产品解说视频指南 |
| 9 | Scalio | https://scalio.app/AI-Prompts | AI 白底商品图 Prompt |
| 10 | Kumba AI | https://kumba.ai/blog/prompt-engineering-for-ai-images | Prompt 8 层公式 |
| 11 | MagicShot | https://magicshot.ai/blog/image-prompt-engineering-2026 | 负面提示词框架 |
| 12 | PrompTessor | https://promptessor.com/blog/ai-image-prompts-better-ai-art-2026 | AI Prompt 负面约束 |
| 13 | AutoKeyWorder | https://autokeyworder.com/blog/ai-inconsistency/ | 去文字约束实证数据 |
| 14 | Luma Labs | https://lumalabs.ai/news/25-ai-product-photography-prompts-ecommerce | 25 条电商 AI Prompt |
| 15 | MiraFlow | https://miraflow.ai/blog/ai-prompts-ecommerce-product-images | 20 条电商 AI Prompt |
| 16 | PhotoRobot | https://www.photorobot.com/blog/enhancing-product-photo-backgrounds-ai | AI 背景生成方法 |
| 17 | 雨果跨境 | https://m.cifnews.com/guide/aliexpress | AE 新手指南（图片/禁限售/尺码表） |
| 18 | 标记侠 | https://www.biaojixia.com | AE 主图尺寸规范 2026 |
| 19 | CSDN | https://blog.csdn.net/shuaishoutu/article/details/139168750 | AE SKU 属性图合规 2026 |
| 20 | iPayLinks | https://www.ipaylinks.com/information_details | AE 店铺发布规则 |
| 21 | Alitools | https://alitools.io/blog/aliexpress-size-chart | AE 尺码表详解 |
| 22 | Alibaba Rules | https://rule.alibaba.com/rule/detail/2054.htm | 商品发布政策（禁限售） |
| 23 | AE IP Protection | https://ipp.alibabagroup.com/infoContent/cn-aliexpress | 知识产权保护规则 |
| 24 | EU DSA | https://digital-strategy.ec.europa.eu/news/commission-makes-binding-alipress-commitments-dsa | 欧盟 DSA 执法 |
| 25 | Vortex IQ | https://docs.vortexiq.ai/attributes/alipress | AE 类目属性完整性 |
| 26 | Brainence | https://brainence.gitbook.io/attributes | AE 属性必填/可选区分 |
| 27 | NovaData | https://novadata.io/resources/blog/amazon-a-plus-content-guide | A+ Content 2026 指南 |
| 28 | Menko Services | https://menkoservices.com/blogs/e-commerce-listing-images-a-content-design | Listing 图 + A+ 设计 |
| 29 | Hera.video | https://hera.video/templates | 电商视频模板 |
| 30 | LlamaGen | https://llamagen.ai/blogs/commercial-storyboard-template | 商业分镜模板 |

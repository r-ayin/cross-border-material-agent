【R3路报告】真实生活场景背景方案 + AI背景稳定性规则（2026-09-28）
通道：web_search/Bing污染弃用，web_fetch直抓权威站全文。✅=直抓核验 ⚠️=推论/未抓到。

== 关键官方结论 ==
1 万相官方i2v公式：图像已定主体/场景/风格，prompt主要描述动态+运镜 → 背景由首帧锚定，i2v不要再重写背景（冲突→重绘变形）。来源 help.aliyun.com/zh/model-studio/text-to-video-prompt ✅
2 背景稳定核心：官方原话「若希望镜头不要发生变化，可以通过固定镜头强调」→ locked/static camera；单镜头写 Generate single shot. ✅
3 Wan2.2-I2V官方模型卡示例背景写法：Blurred beach scenery forms the background featuring... → 虚化背景+列远景元素降几何密度。来源 hf-mirror.com/Wan-AI/Wan2.2-I2V-A14B README ✅

== 三场景 preset（背景段用于首帧image prompt；i2v仅轻量复述一致性句）==
A 阳光卧室（首选，最稳最衬粉裙）：
背景段EN: A cozy sunlit bedroom. A neatly made bed with white linen sits near a large window; sheer pale-beige curtains diffuse the morning light. A potted monstera stands in the corner, a wooden nightstand holds a folded blanket, and a full-length mirror leans against a soft cream wall.
光线段EN: Soft natural window light from camera left, warm morning tone, low contrast, gentle rim light on the figure, slightly overcast daylight.
杂物(增真实感): 皱褶床品一角/翻开书/窗台绿植/拖鞋/半开衣柜门/相框。风险: 床柜直线直角易扭曲、镜子倒影错乱、窗帘纹理闪烁 → 床与镜放画面边缘或被人物遮挡；虚化背景句式；locked camera+人物小幅运动。折中: neatly made bed with a rumpled corner。官方白天示例即白床+米窗帘+窗光组合✅。
B 城市街边（真实感最强但风险最高，仅锁镜头+全虚化人车时尝试）：
背景段EN: A city sidewalk beside a boutique café storefront. Blurred pedestrians and slow-moving traffic form a soft background; a green planter box and a striped awning anchor the foreground, while a brick wall and a distant crosswalk recede behind. Overcast diffuse light wraps the scene.
光线段EN: Soft overcast daylight, low saturation, cool-neutral tone, flat even lighting, no harsh shadows.
风险: 人流车流最大崩坏源；招牌文字乱码 → 人车一律 blurred/out of focus、不写具体数量、招牌写 illegible 或只写 storefront。官方城市示例即虚化人群✅。
C 咖啡店室内（备选，论证优于天台/公园：光线可控、无树叶闪烁、栏杆透视风险低）：
背景段EN: A cozy café interior. A wooden table with a ceramic coffee cup anchors the foreground; blurred shelves of cups, a chalkboard menu, and warm pendant lights recede behind. A leafy potted plant sits by a foggy window with soft daylight filtering through.
光线段EN: Warm mixed light: soft window daylight plus low pendant lamp glow, low contrast, gentle side light, warm tone.
风险: 桌椅直线扭曲(放前景下方/虚化)、吊灯摆动(写static pendant lights)、黑板文字乱码。
稳定性排序(低→高崩坏): 咖啡店≈卧室<街边；真实感排序相反。主推卧室、备选咖啡、街边谨慎。

== 背景稳定性写法清单 ==
1 locked/static/fixed camera（官方✅）2 Generate single shot.（官方✅）3 i2v只写motion+camera不重写背景（官方公式✅）4 "Blurred…forms the background"+远景元素+out of focus（Wan2.2官方示例✅）5 运动用程度副词slowly/gently控幅度（官方✅）6 避免环绕/快速平移/穿越大幅运镜（官方✅）7 背景多软材质(curtains/plant/linen)少硬几何(shelves/grid/tile/text)（⚠️推论）8 镜面/玻璃写 reflection blurred/foggy glass（⚠️推论）9 prompt_extend慎用（智能改写可能给背景加料；官方✅风险⚠️）10 happyhorse无negative_prompt→正向末尾: keep background unchanged and stable, no background morphing, consistent background texture（链路约束✅句式⚠️社区通用）。注: wan2.7原生支持negative_prompt≤500字符✅但happyhorse不支持（项目记忆✅）。

== 粉裙配色结论（99designs色轮✅）==
衬粉裙: 米白/暖象牙/奶油墙(明度差干净)；暖木/浅原木(pink+brown推荐组合)；深海军蓝/葡萄干蓝(Pink and Raisin高对比显高级)；低饱和绿/苔绿(邻近色)；暖金黄昏调(golden hour蜜桃粉统一暖调,万相官方示例✅)。
避免: 正红(同系高饱和打架⚠️)；荧光绿/亮黄(三色组跳脱⚠️)；纯灰/水泥灰(发灰发闷+无生活道具=假,用户已否✅)；冷青蓝/冷紫(色温割裂肤色偏色⚠️)；高对比黑白网格条纹(几何扭曲闪烁)。
总原则: 背景低饱和+与粉拉开明度差+暖调或互补深色，避免第二个高饱和色争艳。

== 首帧-场景衔接7条 ==
1 背景在首帧(wan2.7)写定，i2v只复述一致性句(如 the sunlit bedroom background remains stable and unchanged)其余给运动+运镜（官方✅）
2 首帧9:16与i2v一致；背景元素靠边/虚化让出人物运动空间（Wan2.2 size跟随输入图✅）
3 首帧埋implied motion（手刚抚过裙摆中段/侧身半转），i2v接 the woman continues to gently sway, fabric flowing softly（项目记忆✅+官方✅）
4 首帧光线方向=i2v光线方向，禁止i2v改光源（官方美学一致性✅）
5 负面约束全正向写末尾: background stays stable and consistent, no morphing, no flickering textures（链路✅）
6 首帧背景杂物3-5件为限（细节多→时序压力大；官方卧室示例即床+窗帘+窗+少量✅）
7 prompt_extend慎用/关闭以精准控背景（官方✅风险⚠️）

== 来源 ==
✅: 万相文生/图生Prompt指南、万相2.7图生视频使用指南、万相2.7文/图生视频API参考×2、万相2.1-2.6首帧API参考、Wan2.2-I2V模型卡(hf-mirror)、99designs 33 Color Combinations、Shopify UGC、Sprout UGC。
⚠️未获取: Wikipedia golden hour、HF主站、Runway guide(403)、Luma docs、colormeanings(网关拦)、expertphotography(404)、独立社区背景一致性实测文（结论依据官方公式+示例外推）。
局限: happyhorse独立文档缺失，写法=万相同源外推+项目记忆实测；建议首帧后小样实测 locked camera+虚化背景 组合。

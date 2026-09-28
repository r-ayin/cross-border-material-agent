【R1路报告】妆容+饰品+发型细节词汇（2026-09-28）
验证等级: [A]原文直抓/词表; [B]官网meta直抓正文JS未取; [C]推断。通道: web_search污染; Bing中文被劫持; 可达=help.aliyun.com/allure.com(raw sitemap)/raw.githubusercontent/api.github/cosmopolitan。
来源: 万相官方视频Prompt指南[A]+API参考[A]; OneButtonPrompt词表CSV(accessories/hairstyles/hairdescriptors/haircolors/body_types/humandescriptors)[A]; Allure 21篇meta[B]; EasyNegative[A旁证手部崩坏]。

== 1 妆容谱系(风格/skin/blush/lip/brow/eye/人设) ==
clean girl(no-makeup makeup): natural skin texture healthy glow / soft peach blush on apples of cheeks / sheer rosy lip tint glossy nude / natural fluffy brows brushed up / thin brown eyeliner curled lashes no heavy shadow → 邻家日常晨间卧室,粉裙首选 [B allure no-makeup-makeup教程×2 + A词表]
K-beauty glass skin: dewy glass skin luminous well-moisturized / gradient soft blush内深外浅 / glossy gradient water-color lip / straight soft brown brows / shimmer-free soft shadow glossy lids → 韩系精致特写 [B allure glass-skin, keywords原文含glass skin dewy highlighter]
glazed donut: glazed glowy shiny skin / warm peach glow / glossy glazed lips → 网红强光高级光泽 [B allure glazed-donut×2]
latte拿铁妆: warm-toned even complexion soft matte glow / warm bronzy blush / brown-lined lips topped with clear gloss / softly arched groomed brows / muted coffee monochromatic shadow → 暖调街边咖啡店,与粉柔和撞色 [B allure latte-makeup "monochromatic statement in muted coffee hues"]
soft glam: airbrushed smooth base satin / sculpted blush subtle contour / satin nude-rose lipstick / defined arched brows / soft smoky neutral winged liner full lashes → 精致晚间女神感 [B+C]
barbiecore: flawless luminous base / bright pink blush / magenta lipstick → 粉系同色强化,粉裙+粉妆易腻只取其一 [B]
stained-glass blush: three shades layered contour+brighten, sun-kissed across cheeks and nose bridge → 元气夏日街边 [B]
中式白开水妆=[C未验证] 英文等价 clean girl/"your-skin-but-better"(等价关系为训练知识)。
嵌入短语: clean girl三条全低险; glass skin低险(特写高光点中险帧间漂移); latte低险; graphic winged eyeliner中险(不对称); colorful false eyelashes高险(细密结构i2v闪烁粘连)。

== 2 饰品表(品类/EN/风险) ==
风险依据: 万相API官方negative示例原文含「残缺多余手指比例不良」[A]→手部邻近饰品升档; EasyNegative旁证[A]; 细链/对称/小高频结构时序闪烁[C]。
低险: small gold hoop earrings / chunky gold hoops catching the light(侧脸转动反光出效果★★★); delicate pearl stud earrings(太小可能被忽略); pearl hair claw clip/gold hairpin; slim velvet headband; a small flower tucked behind her ear(田园卧室晨光★★★)。
中险: a delicate gold pendant necklace at her collarbone(领口视觉锚点★★★,delicate比thin chain稳); a slim gold bracelet on her wrist(手部入镜做动作升_high_); a slim minimalist wristwatch(minimalist降复杂度); a slim black choker(颈部转动宽度易变)。
高险(禁): 手指戒指(官方点名手部高危+带货常做抚裙动作); layered dainty necklaces多层细链(交叉断裂融合); stacked bracelets; dangling earrings swaying(与脸颊头发穿插漂移); sheer neutral pink shiny manicure美甲(手指+纹理双高危,仅手部特写值得); delicate hair chain; 肩背包(背带穿插,15s单镜头建议不带)。
总原则[C]: 全身镜头最多2件(耳环+项链即够); 优先头部邻近低险件; 材质gold/pearl>silver/rhinestone; 禁品牌logo与文字饰品。

== 3 发型 ==
形态: long straight silky / liquid hair(sleek mirror-shiny fluid sheen, allure原文[B]); long wavy chestnut hair(万相官方示例原句[A],粉裙最搭波浪增动态); glossy jet-black middle parted(官方「发丝乌黑柔顺」[A]); sleek low ballet bun middle parted(clean girl标志, Scandi Slick[B]); half-up half-down soft face-framing layers[A词表]; long layered hair[A词表]; 发色 rich dimensional brunette tones(expensive brunette原文[B]) / warm caramel highlights[A词表]。
质感词[A词表全表]: Shiny Silky Flowing Layered Voluminous Wavy Curly Luminous Glowing Radiant Fluffy Elegant Graceful Hyperdetailed。
动态(i2v, 万相官方例句直译[A]): her glossy black hair strands sway gently in a light breeze(低险); her long hair brushed by her fingertips, strands catching delicate shine(中险手+发交互); her long hair flows and settles fluidly behind her as she turns(中险,转身写slow/graceful)。禁: hair flying wildly(甩发+百褶同时动=时序崩坏叠加)[C]; 发饰+散发同时大幅运动。
身材脸部基础词[A词表原词]: slender/petite/elegant/hourglass figure/very tall long legs/athletic/fit → 推荐 a slender, elegant young woman with long legs; 气质脸 drop-dead gorgeous/photogenic/graceful/refined/radiant/delicate facial features。

== 4 组合示例(character段60-90词, wan2.7首图) ==
示例1卧室晨光clean girl全低险(77词): A slender, elegant young East Asian woman in her early twenties with delicate facial features and long legs. Dewy glass skin with a healthy natural glow, soft peach blush on her cheeks, sheer glossy nude-pink lips, natural fluffy brows brushed upward, minimal eye makeup with thin brown eyeliner and curled lashes. Long silky black hair, middle parted, falling loosely over her shoulders with a glossy sheen. Small gold hoop earrings and a delicate gold pendant necklace at her collarbone.
示例2街边latte(66词): A graceful young woman with an hourglass figure wearing warm-toned latte makeup: monochromatic muted coffee eyeshadow, warm bronzy blush, lips lined in soft brown topped with clear gloss, softly arched groomed brows. Rich dimensional brunette hair styled in a sleek low ballet bun with loose face-framing strands catching the sunlight. Pearl stud earrings and a slim minimalist wristwatch. Natural luminous skin texture, photogenic and refined. (手表仅手臂入镜保留)
示例3特写glazed(62词): A photogenic young woman with glazed, glowy skin and subtle highlighter shimmer on her cheekbones. Glossy gradient tinted lips, straight soft brown brows, shimmering champagne eyeshadow. Liquid hair — sleek, mirror-shiny, with fluid strands and plenty of sheen as it catches the light. A small flower tucked behind her ear, delicate pearl stud earrings. Radiant, refined, drop-dead gorgeous features. (微闪特写静态安全,进i2v动作要小)
i2v骨架(官方公式运动+运镜,外观不重复): She slowly turns in place, her pink pleated skirt flowing outward; her glossy hair strands sway gently in a light breeze, catching delicate shine. Slow push-in camera, single continuous shot. Generate single shot.

== 5 TL;DR ==
1 素的解法=五粒度(skin/blush/lip/brow/eye)各1短语共25-35词,复用Allure趋势词比beautiful makeup信息量高一个量级。
2 饰品安全区=大圈耳环+单层短项链+发夹发花; 禁区=戒指/多层细链/叠戴手镯/摇曳耳坠/美甲(手部=官方negative点名区[A])。
3 发型动态用万相官方例句直译, 禁wild flying。
4 身材脸部用OneButtonPrompt词表原词(大规模生图验证过响应)。
5 未验证: 白开水妆中文源/soft glam全谱/风险档量化崩坏率(机制推断[C])。

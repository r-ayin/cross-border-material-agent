【R2路报告】身材比例+脸部+皮肤质感 Prompt工程（2026-09-28）
信源：万相官方视频/文生图Prompt指南×3、happyhorse-1.1-i2v官方模型页、Wan2.2 README、kling-prompt-engineering手册(10章)、flaqai/awesome-kling-4-0(52条prompt)、本地qianwen技能文档=★★★/★★已验证；Runway/Kling官方正文/Wikipedia焦距研究=未获取(推断标★)。

== 1 身材词表 ==
安全区(★★★官方例文用过): natural body proportions/naturally proportioned figure(防畸变第一锚点,对应官方负向清单正向化); slender build/slim graceful figure(不触性感化); toned(lightly toned healthy); graceful upright posture/poised stance(体态词比身材词更出博主气质); about 165-170cm tall, healthy weight(Kling角色卡量化锚★★); long-legged silhouette via 服装结构(高腰线表达腿长,不写身体部位★); balanced figure/average build保底。
禁忌区: sexy/hot/sultry/seductive(平台过滤宁杀勿纵,被拒=链路报废★★); curvy/busty/big breasts/thick thighs/tiny waist/extreme hourglass(部位夸张=畸变+擦边); supermodel body/perfect body(反空话无效词+超模感与目标相反); skinny/very thin(病态瘦审核风险★); 中文部位词混写; 任何否定句防畸变(happyhorse无negative字段+否定召唤概念→必须正向 natural proportions/limbs anatomically correct★★★)。
万相3.0官方负向清单参考(wan2.7可用,happyhorse不可用): 不要人脸变形/换脸/多余手指/肢体扭曲/穿模; 不要夸张肢体动作/夸张眨眼。

== 2 脸部 ==
微笑分级(全有官方背书): ①faint tired half-smile(UGC真人感最强,flaqai护肤原文★★) ②soft relaxed smile(万相★★★) ③gentle closed-lip smile, mouth corners slightly lifted(渐变式微笑比静态活★★★) ④bright genuine smile, eyes slightly crinkled(★★★) ⑤relaxed confident smile(博主体感非超模感官方词★★★)。
眼神: gaze softening as she looks into the lens; eyes with moist light reflection(双眸含光★★★); glances down briefly then back to camera(★★); looking off-camera then turning back with a knowing look(★★★)。
眨眼: 只能写 one natural blink/a single slow blink(官方负向列「不要夸张眨眼」=已知失败模式★★★)。
组合句: 情绪不写标签写可观察行为(flaqai: inhale pauses, eyes widen slightly, grip loosens, then shoulders settle★★)。
Face stability(i2v防脸漂移): ①首帧承载身份,视频prompt不重复静态长相(重复=漂移指令;Kling Source-Carries-State★★+官方公式★★★)→外貌只留一句锁定句; ②锁定句官方写法: her face, hairstyle and outfit remain completely consistent throughout(万相「面部特征完全锁定」★★★); ③近景×剧烈运动=脸崩二者不可兼得(Kling故障库❌→✅实证: 近景奔跑脸崩→改中景+保持面部结构不变修复★★)→旋转用knee-up中景+匀速; ④微表情是各家i2v弱项→脸的动作预算小(15s=1眨眼+1微笑渐变足够★★); ⑤多段生成每段≤5s用原始参考图重新锚定; ⑥近景locked camera/极慢推+减少头部转动; ⑦happyhorse-1.1官方宣称改善「ID跨片段保持」→脸漂移风险主要在大幅动作+近景组合而非模型★★★。

== 3 皮肤质感 ==
模型差异: happyhorse-1.1官方宣称提升人物皮肤质感/ID保持/动作流畅→皮肤词值得写★★★; wan2.7-image-pro复杂指令遵循强长prompt吃得下→角色段写满皮肤细节★★★。
官方验证词(★★★万相3.0例文原文): translucent dewy skin with ultra-realistic texture, fine vellus hair visible; realistic skin texture with visible pores, peach fuzz and subsurface scattering; natural flush on cheeks and ears; dark-brown irises with real texture and moist light reflection; individually distinct natural lashes and brows; natural luminous skin tone。
社区反塑料词(★★Kling 22d): unfiltered skin, no-makeup-look base; pores visible; visible fine lines around eyes, slight under-eye shadows(不完美=真实); peach fuzz on cheek catching backlight; 瑕疵库每角色≥2: light freckles across the nose/faint under-eye shadow/a few flyaway strands at the temple/natural lip texture; flaqai UGC金标准: natural pores and faint under-eye texture / ordinary smartphone exposure / no beauty-ad sparkle。
真实相机锚定(★★Kling 22a替代空话): Fujifilm X100V look, natural color, light film grain(博主感首选); Kodak Portra 400 warm soft skin tones; Canon EF 85mm f/1.2 shallow DoF; Sony A7 50mm f/1.8 natural daylight。
禁用词(推塑料): flawless skin/porcelain skin/perfect smooth skin/airbrushed/beauty filter/soft-focus skin/creamy perfect complexion/磨皮美颜类; 8K/masterpiece/best quality(图像遗产词视频无效稀释权重,一个字别写★★)。
妆容: 写具体妆效不写「精致妆容」: light natural makeup: sheer base, soft peach blush, nude-pink lip tint, clean brow shaping, subtle brown eyeliner(★★+★)。

== 4 距离-脸崩(竖屏) ==
定性(多源一致★★/★★★): 景别越远脸越不可要求(极远景不要求面部表演); 脸崩主因=近景×剧烈运动乘积; 全身镜头脸必然小→放弃脸部表演把情绪放进体态(Kling算力分配: 大胆运动以面部细节为代价); 脸稳定靠首帧锚定+锁定句; 运动幅度与身份保真是预算关系(大动作段微笑渐变+眨眼选1主1次)。
量化推断(★几何推算): 1080P全身脸约110-135px=皮肤词失效; knee-up脸约210-300px=微表情/皮肤开始可辨=裙子完整×脸可辨最佳平衡带; waist-up脸330-450px全生效; 特写>400px必须锁镜头。实操: 15s单镜头取knee-up~全身之间; 全身则脸=氛围级, 皮肤词写首帧(wan2.7高分辨率出图有效), 视频段只留锁定句+1微笑渐变。焦距: 官方人脸近景例全用85mm长焦浅景深、场景建立24mm; 首帧写50-85mm防脸部透视畸变(★★★间接)。

== 5 完整示例 ==
首帧(wan2.7,9:16,卧室版,105词): Vertical 9:16 lifestyle fashion photo, knee-up framing. A 24-year-old East Asian woman, oval face, soft natural makeup with sheer base and nude-pink lips. Unfiltered skin: visible pores, faint under-eye texture, peach fuzz catching warm window light, light freckles on her nose. Dark-brown eyes with moist light reflection, long black hair with a few loose strands. Slender, naturally toned build, graceful upright posture, about 168cm. Pink high-waisted fine-pleated maxi skirt, white tucked-in knit top, small gold hoop earrings, delicate chain necklace. Mid-twirl: weight on her left leg, right heel lifted, pleats fanning out, one hand lightly brushing her hair, relaxed confident smile. Sunlit bedroom, unmade bed and sheer curtains behind, Fujifilm X100V look, 50mm f/2.8, soft daylight from window left, light film grain.
街边版替换场景句: Tree-lined city sidewalk in the morning, café awning and parked bicycles softly blurred behind her, natural overcast light.
i2v运动prompt(正向only): She completes one gentle continuous twirl, the fine pleats fan outward and settle with a soft swing; she brushes a loose strand behind her ear, gives one natural blink, her relaxed smile gradually warms into a bright genuine smile with slightly crinkled eyes. Camera locked at knee-up framing with a very slow push-in. Warm daylight stays consistent from window left; quiet room tone with faint fabric rustle. Her face, hairstyle, skirt and jewelry remain completely consistent throughout. Single continuous shot.

== 6 行动建议 ==
1 人物「素」的修复在首帧段不在视频段(妆容/饰品/皮肤/身材全写wan2.7首帧;happyhorse只留锁定句)。
2 博主体感三件套: unfiltered skin+pores/peach fuzz/under-eye texture; tired→genuine微笑分级; ordinary smartphone/natural exposure质感词; 禁flawless/porcelain/beauty filter。
3 背景真实地点用三层构图(前景小物+中景人物+背景生活细节); 不完美生活细节=非棚拍最强信号。
4 限流防线: sexy/curvy/busty/tiny waist一律不写; 身材走natural proportions+slender toned+posture。
5 脸崩防线: knee-up中景+匀速+locked/very slow push-in; 特写段单独生成且锁镜头。

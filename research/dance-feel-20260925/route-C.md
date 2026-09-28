【C路报告】AI视频生成「人物运动」Prompt工程调研（wan2.7首图→happyhorse-1.1-i2v，仅正向英文prompt）

== 通道可信度 ==
✅官方一手：阿里云万相Prompt指南(中/英)、万相3.0指南、Runway Academy Prompting Guide(Gen-4.5)、HappyHorse官方介绍。🔶社区高质量：GitHub kling-prompt-engineering手册(26文件，引用02/04/09/10/11/15/18/19/23章)、cliprise awesome-image-to-video-prompts、freeaitool三篇2026指南。❌未验证：可灵官方(docs.qingque.cn JS渲染)、海螺官方(SPA空壳)、Vidu(网关拦截)、Pika、Runway help原文(Cloudflare 403)、Reddit/知乎。

== 1 运动词汇表 ==
1.1 身体动作：performs synchronized dance moves with vibrant energy / complex footwork, explosive power（万相官方街舞示例）；body leans forward, arms swing with maximum range and frequency, one leg pushes off explosively（万相官方跑步示例=逐部位拆解写法）；★万相3.0官方音频驱动舞蹈竖屏9:16示例（与本项目同构，最高参考价值）: crisp, large-amplitude moves and freeze poses on drum beats; soft body waves and hand gestures in calm passages; denser, more explosive moves at the chorus；hip sway, weight shift from one leg to the other（万相3.0扭胯示例）；fabric moves gently in the wind while the body, face and outfit remain stable（cliprise面料-身体分离句式，防穿模关键）；hair and hemline sway with momentum。
1.2 镜头：万相官方运镜情感意图——push-in亲密/紧张；pull-out揭示规模；tracking同行；orbit强调主体；fixed camera静止专注。⚠万相3.0官方警告：环绕运镜弧度≤45°，更大弧度空间畸变。运镜速度→情感（Kling 02）：极慢=庄严；慢=从容优雅；中=自然跟随；快=紧张能量；极快=混乱冲击。
1.3 强度控制：万相官方=幅度+速率+作用效果三要素；i2v公式用quickly/slowly副词控制动态程度；Runway官方强动词+强度副词(aggressive sweeping arc / extremely rapid crash zoom)——强度靠形容动词的方式表达而非空喊dynamic；freeaitool强度分级Low1-3静态/Medium4-6日常/High7-10易变形谨慎；Kling 09/18反面结论：堆dynamic/epic/8K/masterpiece空词不增加运动反而稀释注意力，「动感」必须=具体运动+速度+终点。⚠否定词会把被否定概念植入注意力（「不要跳」仍激活「跳」），gentle/sway字面主导输出——本项目病根实锤。
1.4 节奏写法：Kling 15时间轴三层——状态层(从[起始]→经过[变化]→结束于[终点])；运动层速度曲线(匀速/ease-in/ease-out/缓入缓出/急停)；节奏层能量曲线(渐进▁▂▃▅▇/消退▇▅▃▂▁/脉冲▂▅▁▅▂/长蓄力▁▁▁▁▇/急停▇▁▁▁▁)+BEAT节拍点标记。Runway官方Sequential Prompting: "X occurs, then Y occurs. Finally, Z occurs."或时间戳[00:01]；序列复杂度须与时长匹配。万相3.0：总体描述直接写节奏走向；分镜时间戳[0-3秒]；避免高频动作(一秒摇头3次)；卡点写法=节奏词与动作词绑定。

== 2 结构模板 ==
万相官方i2v公式=运动+运镜（图像已定主体/场景/风格，文字只写动态；不动镜头写fixed camera）。
万相进阶=主体+场景+运动+美学控制+风格化（弱prompt漏美学控制→「未定义空间静止机位」）。
★Runway官方I2V句式="The camera [motion] as the subject [action]. [additional]"——i2v prompt应几乎只写运动；结构顺序不重要，清晰无歧义无矛盾才重要。
Kling i2v最小模板：保持[身份]不变。只有[运动]变化。镜头：[一个运动]。约束：[不能变的]。
cliprise五要素（可直接套happyhorse）：Using the uploaded image as the exact visual reference, create a [N]-second vertical video. Preserve [identity/outfit/composition]. Camera: [one primary movement]. Subject motion: […]. Scene motion: […]. Lighting: […]. Final beat: [ending frame]. Restrictions: [no …]。
总长：freeaitool建议50-150词（核心80-120词，超200词注意力分散）。
负面并入（happyhorse无negative_prompt）：Runway官方第一条Use positive phrasing；Kling 09/18否定只允许在末尾约束槽且只放文字/水印类，质量项一律正向改写；万相3.0负向清单「不必凑数，不重复正向已写明内容」。⇒落地：正文全正向（含质量锚 face stable, natural body proportions, smooth continuous motion, anatomically correct hands）+末尾最小Restrictions（no text, no watermark, no extra people, no clothing change, no warped limbs）。

== 3 时长与动作量（15s安全上限）==
★Kling手册18实测经验值（最硬量化结论）：5s=1个动作节拍；10s=1动作+1反应；15s=最多3个节拍。超密度→压成闪帧/快进/跳切；宁可拆片段不要塞。
万相3.0：多镜头每段2-5秒；避免高频动作；单镜头写"Generate single shot."。
Runway FAQ：意外切镜=时长不够或措辞暗示剪辑；加"Continuous, seamless shot"。
Kling 23首尾帧5秒变化量参考：位移3-5步或横穿一次/转身90-180°/表情一档/光线一色温档；一个主要变化+一个次要变化为上限。
⇒15s节拍预算：0-4s起势(pose+裙摆微动+重心转移)、4-10s主体动作(一个完整舞蹈组合或一次旋转+裙摆展开)、10-15s收尾定格(hero pose+看镜头微笑+裙摆落定)，每拍写清起始/终点状态。

== 4 失败模式与规避 ==
肢体变形/面崩：近景+快速运动同时要求超出保持能力→舞蹈大幅动作⇒中远景+锁定机位（Kling 18案例1、10算力分配「舞蹈主预算给动作幅度，牺牲面部近景」）；wan3官方负面写法参考。
滑步：官方条目未验证；间接=写脚地交互与重心(steps firmly, pivots on the ball of the foot, weight transfers left to right)，避免glide/slide词（推断）。
面部漂移：i2v首帧承载身份、prompt不重复描述长相（Kling 04「图承载身份，文字只承载变化」——重复静态细节反与图打架→漂移）。
衣物穿模：面料与身体分离描述+正向锁定 outfit design, fabric texture and color palette remain unchanged。
动作僵硬/AI味：空话词堆砌→只保留「摄影机/麦克风/测光表/秒表能检测到」的词；只写主体不写运动→画面静止或随机运动；形容词翻译成可见动作。
动作太保守（本项目现状）：①弱动词+否定强动作→换强动词+幅度速度副词+明确终点；②首帧无运动暗示→Runway官方FAQ：首帧implied motion（运动模糊/动作中途姿态/方向线）决定模型运动倾向，首帧完全静止笔直则倾向微动；③声明大幅动作与节拍。
动作悬空：只写过程不写终点→"结束于[明确终点状态]"/Final beat。
自相矛盾：一个维度多个值→速度/光线/方向词每维度只留一个值。
意外切镜：加Continuous, seamless shot。文字乱码：约束槽no text，文字后期加。

== 5 首帧策略 ==
Kling 23好首帧五标准：①构图完整但非高潮瞬间（高潮留给中段/尾帧）；②运动中性：有势能不锁方向（准备动但没决定往哪动；反例深陷沙发双腿伸直）；③Lead Room视线方向留白（站画面右1/3面朝左，左留2/3）；④身份清晰脸不被头发挡；⑤光线色调与后续一致。
Runway官方FAQ（一手）：首帧implied motion与prompt矛盾则需更多迭代；官方案例=移除运动线索后静止prompt才成功→反推：想要大幅律动，首帧应自带运动倾向线索（裙摆轻微扬起、重心偏一侧、身体微前倾、发丝微动）。首帧必须高质量无伪影（模糊的手脸会被放大）。
百褶裙带货首帧落地建议（推断+综合）：双脚非并拢锁死（一腿微屈/自然小步位）、重心落单腿、胯微侧、一手轻撩裙摆或发丝、裙摆有轻微扬起弧度、目光朝留白侧、全身中远景9:16人物略偏1/3。
（happyhorse当前仅首帧驱动；若支持首尾帧：变化量过小→模型随机抖动或几乎不动=「两张图淡入淡出」失败模式。）

== 6 本项目直接落地要点 ==
1 重写video_prompt_en：删gentle/graceful/subtle sway与not energetic dancing；改用万相3.0音频驱动舞蹈强度语言（large-amplitude, crisp moves, freeze poses on the beat, energetic hip sway and twirl, skirt flaring outward）。
2 结构：Runway句式"The camera [motion] as the subject [action]"+cliprise五要素，总长80-150词。
3 节拍：15s≤3个beat，每beat有起始/终点状态；写Continuous, seamless shot. Generate single shot.
4 负面：末尾最小约束槽，质量项全正向锚。
5 首帧配合：wan2.7生首图就埋运动线索（裙摆微扬/重心偏单腿/lead room/全身中远景），否则i2v再强的动词也被静止首帧拖低幅度。
6 预算思维：15s大幅舞蹈=主预算给动作幅度⇒中远景+锁定/缓推镜头，不要面部大特写+快速运动组合。

== 来源 ==
万相官方中: help.aliyun.com/zh/model-studio/text-to-video-prompt; 万相3.0: help.aliyun.com/zh/model-studio/wan3-video-generation-prompt-guide; 万相英: alibabacloud.com/help/en/model-studio/text-to-video-prompt; Runway Academy: academy.runwayml.com/image-to-video-guide; Kling手册: github.com/Yuyyxz/kling-prompt-engineering; cliprise: github.com/cliprise/awesome-image-to-video-prompts; freeaitool三篇; HappyHorse官方: developer.aliyun.com/article/1731726、1731571（15B参数/1080P/3-15s/音画联合/2026-04登顶Video Arena双榜）。

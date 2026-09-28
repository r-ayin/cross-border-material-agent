【B路报告 3/3】风险与禁忌 + 规避写法 + 来源清单

== 3.1 高频崩坏点（按部位/元素）==
1 手指/手部：手按膝/手抓裙摆/手指快速变化必崩（Seedance负面词表含 bad hands, missing fingers, extra digit）→ prompt不写手与身体/衣物精确接触。
2 裙摆穿模：交叉步/深蹲/快速旋转时裙子穿腿或融化；细百褶快速运动中帧间闪烁 → 限慢速单圈转身；裙摆用 flows/settles/sways 连续动词。
3 重心漂移/脚底打滑：滑步(A11)必须写明 flat foot gliding, feet stay grounded，否则溜冰感。
4 旋转涂抹：多圈旋转背景扭曲拖影裙摆实心锥 → 全片最多一次慢速单圈。
5 面部崩坏：甩发遮脸、转身侧脸→正脸过渡五官漂移 → 面部大部分时间朝镜头；转身用匀速单圈。
6 服装一致性：百褶纹理闪烁/裙长突变/颜色漂移 → 末尾加 consistent clothing, stable fabric texture；首图已锁定裙子，prompt只强调 fabric follows the motion，不重新描述款式细节（避免模型重画衣服）。
7 动作过载/描述笼统：15秒塞6+动作→每个只完成一半退化成乱晃；「原地轻微摇摆」病根=Seedance官方诊断的动作僵硬（①缺流畅性/惯性词汇②描述过于笼统）→ 加 natural momentum and follow-through / seamless transitions between moves / breathes with the movement，动作具体到部位+方向+速度。

== 3.2 写法禁忌与规避（happyhorse：仅正向prompt，负面并入末尾）==
1 禁写词汇：jump/leap/fast spin/multiple turns/drop to floor/floor work/touch knee/grab the skirt/whip hair/rapid footwork/high kick。
2 负面→正向改写（正向prompt中no/without/not遵循率不可靠）：
 - 不要肢体变形 → her body proportions stay natural and consistent throughout
 - 不要手部错误 → her hands move smoothly with relaxed natural fingers
 - 不要切镜头 → one single continuous shot, fixed camera（或 slow gentle push-in）
 - 不要裙摆穿模 → the pleated fabric flows and settles naturally around her legs
 - 不要机器人感 → smooth organic motion with natural momentum, she breathes with the movement
3 四层结构模板（Seedance实战文）：场景/灯光 → 人物外观+表情 → 动作序列（first...then...finally...时间序，比形容词堆叠易执行）→ 画质+末尾正向约束。
4 动词具体到部位+方向+速度：反例 she dances energetically；正例 she sways her hips slowly in a figure-8 while her shoulders stay still。
5 每个动作配一句面料响应：the skirt swings/ripples/flares/settles——不写则裙子默认静态贴图。
6 卡点感词汇：hits the beat/on the beat/sharp accents followed by smooth flow；快慢对比比全程快既安全又有网感。
7 表情/视线：每段写明视线（gaze at the camera/eyes follow her hand）；表情呆板修复= expressive face, smiling, eyes following the movement。

== 3.3 对当前视频的最小修复建议 ==
当前「仅原地轻微摇摆」=动作僵硬症状。最小改动：保留首图与人物描述，动作段改写为「4段时间序动作（方案1）+每段一句裙摆面料响应+末尾正向约束串」。

== 已验证来源（全文抓取核验）==
1-9 STEEZY：MOVE摆胯/Wannabe肩hit/Mic Drop滑步/10 Easy Dance Moves/7 TikTok Moves/Whacking三招/7 Popping Exercises/How To Dance Sexy/TikTok拍摄5要点（steezy.co/posts/...）
10 CSDN Seedance2舞蹈生成活人感提示词（四层结构/短语库/排查表/CFG7-11）blog.csdn.net/weixin_32487557/article/details/163939737
11 CSDN TikTok舞蹈视频全解析（i_Ris BPM130-140、2秒3次wave地狱难度、旋转裙摆弧度、卡点对应重拍）blog.csdn.net/weixin_29641609/article/details/164314424
12 DancePlug Why TikTok Dances Dominate（竖屏与1分钟时长而设计、少脚步动作）
未能验证：抖音中文卡点舞/手势舞拆解（知乎403、百度反爬）；pirouette/spotting专项（Wikipedia/WikiHow不可达）；body wave全身专项（仅Seedance文佐证）。

== 网络通道备注 ==
web_search工具被污染不可用；Bing中国区垃圾结果；DDG/Wikipedia/WikiHow连接失败；STEEZY/CSDN/DancePlug可访问全文验证。

# 跨境电商人物短视频提示词完全手册 v1.0
> 任何人照做即可复现「漂亮且真实」的人物短视频提示词。方法经 2026-09-25~09-28 七次真实生成验证（wan2.7-image-pro 生首帧 + happyhorse-1.1-i2v 生视频），同样适配其他文生图/图生视频模型。
> 配套文件：docs/prompt-templates-v5.json（机读模板）、docs/video-motion-prompt-spec.md（规范原文）、scripts/video_pipeline.py（一键管线）。

## 0. 三十秒上手

**一句话总公式**
- 首帧（文生图）= 来源叙事句 + 人物精修层 + 生活化场景 + 动作中途姿态 + 手机机位构图 + 普通窗光 + 排除句
- 视频（图生视频）= 机位与背景一致性句 + 三拍动作段 + 节奏与布料响应句 + 锁定句 + Generate single shot + 排除句

**五步流程**

| 步骤 | 做什么 | 门禁 |
|---|---|---|
| 1 | 用§8 填空公式拼首帧 prompt | 禁写词表§6 全查零命中 |
| 2 | 文生图（wan2.7-image-pro，1080×1920） | — |
| 3 | 目检首帧 | §9.3 七项+附加四项，≥6/7 才放行 |
| 4 | 用§8 视频公式拼 i2v prompt | 只写运动+运镜，背景仅一句一致性复述 |
| 5 | 图生视频（happyhorse-1.1-i2v，15s/1080P）→ 抽帧 QA | §9.4 八项全过才交付 |

**三条铁律（违反必翻车）**
1. **背景只写首帧**：i2v 阶段重写背景会与首帧冲突→背景扭曲（官方公式：i2v prompt=运动+运镜）。
2. **不堆瑕疵词**：雀斑/毛孔/做旧=艺术摄影语义→「刻意感」；真实感靠「拍摄过程叙事」（谁拍/用什么拍/什么状态）。
3. **不用否定句**：happyhorse-1.1-i2v 没有 negative_prompt 字段，所有约束正向化放句尾（No text… 这类排除句在 wan2.7 首帧可用，i2v 阶段一律正向锁定句）。

## 1. 五大核心原理（含根因）

| # | 原理 | 根因/证据 |
|---|---|---|
| 1 | 拍摄过程叙事 > 质量形容词堆叠 | 描述「照片来源」比说 realistic/8K 更有效：来源词自带一整套摄影逻辑（CSDN 全文核读★★★） |
| 2 | 背景锚定 | 万相官方：i2v prompt=运动+运镜；背景由首帧锚定，重写=重绘扭曲 |
| 3 | 运动三拍骨架 | 15s=3 主拍、可感知变化≤5；强动词+稳定副词+每拍起止状态；弱动词+否定句+静态首帧=三重锁死（平淡视频根因） |
| 4 | 脸部距离预算 | 全身景=脸部氛围级；膝上=脸戏平衡区；特写×剧烈运动禁止同现；15s 脸部预算=1 次自然眨眼+1 次微笑渐变 |
| 5 | 真实=轻美颜精修，而非瑕疵堆叠 | 抖音/小红书带货爆款=磨皮 30-50% 的匀净微光泽肌；「可见毛孔/雀斑」是反差赛道语言；瑕疵词堆叠=刻意做旧（CSDN★★★） |

## 2. 人物关键词库（首帧用）

> 用法：按槽位取词组句；每槽 1 句；精修层整段复用不要拆。

| 槽位 | 中文含义 | 英文关键词（直接可用） | 备注 |
|---|---|---|---|
| 来源/设备 | 手机相册随手拍、原相机直出 | casual phone snapshot from a phone album / raw camera look / unedited / everyday photo | 最有效的一类词★★★ |
| 机位 | 胸高支架、轻微内倾、广角畸变 | camera at chest height tilted slightly inward / slight wide-angle phone distortion | 穿搭视频原生机位★★ |
| 脸·精修层 | 轻美颜：水光匀净肌+精致五官 | smooth luminous even skin with a gentle dewy glow / delicate symmetrical facial features / softly contoured oval face / clear bright dark-brown eyes / subtle brown tightline / curled defined lashes / neatly groomed natural arched brows / seamless soft peach blush gradient / glossy gradient nude-pink lips with a crisp lip line | v7 定版整段；「精致但不塑料」的平衡点 |
| 头发 | 黑长直中分+松散发丝光泽 | long silky black hair, middle parted / falling loosely over her shoulders with a few stray strands / glossy sheen | 发丝是 i2v  Motion 的免费动势 |
| 饰品 | ≤2 件安全区 | small gold hoop earrings / delicate gold pendant necklace at collarbone | 手部=官方高危区：戒指/多层链/叠戴手环/垂坠耳环/美甲全禁 |
| 身材体态 | 自然匀称+挺拔 | slender naturally toned build / graceful upright posture / about 168cm / natural body proportions | sexy/curvy/tiny waist/supermodel 全禁 |
| 状态 | 动作中途+不看镜头 | caught mid-motion / gaze directed slightly past the camera / relaxed faint half-smile / not a posed smile | 「假装不知道被拍」=活人感★★★ |
| 构图 | 偏心+脚贴底+前景遮挡 | subject slightly off-center to the right / feet near the bottom edge with headroom above / a softly blurred door-frame edge cropping the extreme left foreground / partial crop | AI 默认居中=橱窗样品脸 |
| 服装保真 | 引用参考图只保服装 | She wears the exact < garment > from the two reference photos (garment references only: preserve pleats, waistband, drape and hem proportions) | 带货必写：商品一致性锚 |

**已废弃词（v2.1 旧路线，用了就「刻意」）**：freckles / visible pores / faint peach fuzz / Fujifilm X100V look / 50mm f/2.8 / light film grain → 艺术摄影语义，模型按「被强调的局部细节」渲染，强度失控。

## 3. 场景关键词库

**生活化三信号**：①使用痕迹 ②随机摆放 ③「正在使用」的道具。样板间美学（cream wall+monstera/对称陈列/色卡软装/挂毯三件套）=0.1 秒广告识别信号，全禁。

| preset | 背景句（整段可用） | 光线句 |
|---|---|---|
| 卧室（首选，已定版） | Background: unmade bed with the duvet rumpled at one corner near the frame edge, a couple of clothes draped over a chair back, charging cable and a water bottle on the nightstand, a half-drunk iced coffee on a small desk, plain lived-in cream-white walls; all background elements gently out of focus; only these listed items are present, no tripod, no phone, no camera gear visible in the scene. | Soft daytime window light through a sheer curtain, diffused, auto exposure, slightly uneven brightness with the window side clipping a little, warm-ish white balance. |
| 街边（谨慎，已定版） | Background: tree-lined city sidewalk in the morning, a cafe awning and parked bicycles softly blurred behind her, a green planter box at the frame edge, plain lived-in storefront walls; all background elements gently out of focus; pedestrians and traffic blurred and out of focus; only these listed items are present, no tripod, no phone, no camera gear visible in the scene. | Soft overcast daylight, low saturation, flat even lighting, auto exposure, slightly uneven brightness, warm-ish white balance. |
| 咖啡店（未定版） | 场景稳定性与卧室相当但光线/道具未经实测；管线 init 传 cafe 会被拒绝 | — |

**小杂物白名单（3-5 件、随机摆放、略乱≠脏乱差）**：rumpled 被角 / 椅背搭衣 / 充电线 / 水瓶 / 半杯冰美式 / 翻开的书 / 手机反扣桌面。
**配色**：衬托粉裙=奶油白/暖木/藏青/苔绿/晨光金；禁=纯灰影棚/正红/荧光色/冷紫/黑白格。

## 4. 光线与运镜禁写/推荐对照

| 想表达 | ❌ 禁（广告/艺术摄影语义） | ✅ 推荐（手机原生语义） |
|---|---|---|
| 光 | golden hour / rim light / studio light / cinematic lighting / 布光设计词 | window light through sheer curtain / diffused / auto exposure / slightly uneven brightness / window side clipping a little / overcast daylight |
| 相机 | Fujifilm X100V / 50mm f/2.8 / film grain / 8K / masterpiece | raw camera look / phone propped up out of frame / slight wide-angle phone distortion |
| 运镜(i2v) | 环绕/快速平移/推拉变焦 | fixed full-body camera / locked camera / static camera / the camera keeps the same full-body distance from head to shoes throughout with no zoom-in |

## 5. 动作库（视频 i2v 用）

**三拍骨架（15s 标准）**

| 拍 | 时间 | 内容模板 | 示例动词链 |
|---|---|---|---|
| 1 | 0-5s | 起势律动 | grooves in a relaxed two-step, bouncing lightly on the beat → flows into a slow figure-8 hip sway |
| 2 | 5-10s | 展开+裙摆开花 | sweeps one arm in a fluid wave → frames her head with both arms overhead → one slow graceful turn on the balls of her feet, the skirt flaring outward in a full circle |
| 3 | 10-15s | 收势定格+脸部预算 | faces the camera as the skirt settles → tucks a strand of hair behind her ear → holds a confident final pose → relaxed smile warming into a bright genuine smile with one natural blink, eyes meeting the lens |

**强动词表（✅）vs 弱动词黑名单（❌）**

| ✅ 强动词 | ❌ 弱动词/否定 |
|---|---|
| sweeps / flows / flares / fanning / pops / planted / glances / tucks / shifts / hits / twists | gently move / slightly sway / don't move / no motion / avoid |

**四类必带句**
1. 布料响应：the pleats rippling like soft waves around her legs / the skirt flaring outward in a full circle / pleats fanning open
2. 动停对比：sharp stops contrasting with flowing movement / crisp accents followed by smooth flow / stops abruptly, feet planted, momentum carrying her hair and skirt forward before settling
3. 首帧中途姿态（文生图侧）：weight shifted onto one leg with the other heel lifted / the skirt hem still settling from a small step / one hand raised smoothing a loose strand
4. 锁定句（i2v 尾部整段）：Her face, hairstyle, skirt and jewelry remain completely consistent throughout, natural body proportions, feet grounded, background texture stable with no morphing and no flickering. + One continuous seamless shot, Generate single shot. + 走位类加全身锁：the camera keeps the same full-body distance from head to shoes throughout with no zoom-in

## 6. 禁写词总表（分类+后果）

| 类别 | 禁词 | 后果 |
|---|---|---|
| 身体风险 | sexy hot sultry seductive curvy busty thick thighs tiny waist hourglass extreme supermodel body perfect body skinny very thin | 平台风控+审美崩坏 |
| 塑料感 | flawless skin porcelain skin airbrushed beauty filter soft-focus skin 8K masterpiece best quality | 假人感/恐怖谷 |
| 瑕疵堆叠 | freckles visible pores peach fuzz under-eye texture（作为强调特征时） | 刻意做旧/雀斑妆 |
| 艺术摄影 | Fujifilm X100V 50mm f/2.8 film grain cinematic lighting studio light golden hour rim light | 摆拍大片感≠UGC |
| 手部高危 | rings layered dainty necklaces stacked bracelets dangling earrings manicure details brand logo | 手指崩坏高发区 |
| 发型失控 | hair flying wildly | 逐帧漂移 |
| 构图模板 | perfectly centered / symmetrical composition / looking at camera smiling（定格摆姿语义） | 橱窗样品脸 |

## 7. 完整示例（五段定版全文，可直接复制）

### 7.1 首帧·卧室 v7（367 词）
Casual phone snapshot from a phone album, vertical 9:16, raw camera look, unedited, everyday photo. A young East Asian woman in her early twenties in her own lived-in bedroom, caught mid-motion: one hand raised smoothing a loose strand of hair near her ear, weight shifted onto one leg with the other heel lifted, the pink pleated skirt hem still settling from a small step; her gaze directed slightly past the camera with a relaxed faint half-smile, as if caught between movements, not a posed smile. Her face is refined and softly polished by a light beauty filter: smooth luminous even skin with a gentle dewy glow, delicate symmetrical facial features, softly contoured oval face, clear bright dark-brown eyes with a subtle brown tightline and curled defined lashes, neatly groomed natural arched brows, seamless soft peach blush gradient on the cheeks, glossy gradient nude-pink lips with a crisp lip line. Long silky black hair, middle parted, falling loosely over her shoulders with a few stray strands, glossy sheen. Small gold hoop earrings and a delicate gold pendant necklace at her collarbone. She wears the exact soft blush-pink high-waist fine-pleated maxi skirt from the two reference photos (garment references only: preserve pleats, waistband, drape and hem proportions), an opaque cream short-sleeve knit top tucked in without covering the waistband, and neutral closed-toe flat shoes, both feet fully visible in frame. Subject slightly off-center to the right, feet near the bottom edge with headroom above, a softly blurred door-frame edge cropping the extreme left foreground, slight wide-angle phone distortion, camera at chest height tilted slightly inward. Background: unmade bed with the duvet rumpled at one corner near the frame edge, a couple of clothes draped over a chair back, charging cable and a water bottle on the nightstand, a half-drunk iced coffee on a small desk, plain lived-in cream-white walls; all background elements gently out of focus; only these listed items are present, no tripod, no phone, no camera gear visible in the scene. Soft daytime window light through a sheer curtain, diffused, auto exposure, slightly uneven brightness with the window side clipping a little, warm-ish white balance. No text, no logo, no watermark, no extra people, no plastic skin.

**逐句对应原理**：句1=来源叙事(原理1)；句2=中途姿态+不看镜头(原理3/活人感)；句3=精修层(原理5)；句4-5=头发饰品；句6=服装保真锚；句7=手机机位构图(原理1)；句8=生活化场景(§3)；句9=窗光自动曝光(§4)；句10=排除句。

### 7.2 首帧·街边 v7（352 词全文；与 7.1 仅三处替换：场景句/背景段/光线段，其余逐字相同以保证人物一致性）
Casual phone snapshot from a phone album, vertical 9:16, raw camera look, unedited, everyday photo. A young East Asian woman in her early twenties on a lived-in city sidewalk, caught mid-motion: one hand raised smoothing a loose strand of hair near her ear, weight shifted onto one leg with the other heel lifted, the pink pleated skirt hem still settling from a small step; her gaze directed slightly past the camera with a relaxed faint half-smile, as if caught between movements, not a posed smile. Her face is refined and softly polished by a light beauty filter: smooth luminous even skin with a gentle dewy glow, delicate symmetrical facial features, softly contoured oval face, clear bright dark-brown eyes with a subtle brown tightline and curled defined lashes, neatly groomed natural arched brows, seamless soft peach blush gradient on the cheeks, glossy gradient nude-pink lips with a crisp lip line. Long silky black hair, middle parted, falling loosely over her shoulders with a few stray strands, glossy sheen. Small gold hoop earrings and a delicate gold pendant necklace at her collarbone. She wears the exact soft blush-pink high-waist fine-pleated maxi skirt from the two reference photos (garment references only: preserve pleats, waistband, drape and hem proportions), an opaque cream short-sleeve knit top tucked in without covering the waistband, and neutral closed-toe flat shoes, both feet fully visible in frame. Subject slightly off-center to the right, feet near the bottom edge with headroom above, a softly blurred door-frame edge cropping the extreme left foreground, slight wide-angle phone distortion, camera at chest height tilted slightly inward. Background: tree-lined city sidewalk in the morning, a cafe awning and parked bicycles softly blurred behind her, a green planter box at the frame edge, plain lived-in storefront walls; all background elements gently out of focus; pedestrians and traffic blurred and out of focus; only these listed items are present, no tripod, no phone, no camera gear visible in the scene. Soft overcast daylight, low saturation, flat even lighting, auto exposure, slightly uneven brightness, warm-ish white balance. No text, no logo, no watermark, no extra people, no plastic skin.

### 7.3 视频·T01 全身律动展示（212 词）
Vertical handheld vlog-style clip, fixed full-body camera, the sunlit bedroom background remains stable and unchanged, softly blurred behind her. The young woman in the pink high-waist fine-pleated maxi skirt grooves in a relaxed two-step, bouncing lightly on the beat, then flows into a slow figure-8 hip sway, the pleats rippling like soft waves around her legs. She sweeps one arm in a fluid wave and frames her head with both arms overhead, chest open, chin lifted, then performs one slow graceful turn on the balls of her feet, the skirt flaring outward in a full circle, pleats fanning open. Finally she faces the camera as the skirt settles softly, tucks a strand of hair behind her ear and holds a confident final pose, weight on one leg, hip slightly out, her relaxed smile warming into a bright genuine smile with one natural blink, eyes meeting the lens. One continuous seamless shot, Generate single shot. Crisp accents followed by smooth flow, smooth organic motion with natural momentum, her glossy hair strands sway gently with her movement. Her face, hairstyle, skirt and jewelry remain completely consistent throughout, natural body proportions, feet grounded, background texture stable with no morphing and no flickering. No text, no watermark, no extra people, no clothing change, no warped limbs.

### 7.4 视频·T02 走位互动展示（含全身锁句，231 词）
Vertical handheld vlog-style clip, fixed full-body camera, the camera keeps the same full-body distance from head to shoes throughout with no zoom-in, the sunlit bedroom background remains stable and unchanged, softly blurred behind her. The young woman in the pink high-waist fine-pleated maxi skirt walks confidently toward the camera in a straight line, hips leading each step, the skirt hem swaying with every step, then stops abruptly, feet planted, momentum carrying her hair and skirt forward before settling. She holds a sharp confident hip pop in an A-line stance, fingertips resting lightly on her waistband, then lifts the sides of her skirt with both hands and performs one slow graceful turn, the pleats fanning open in a full circle. The turn ends with her back to the camera, the skirt settling softly, and she glances back over her shoulder, head turning last, eyes meeting the lens, her relaxed smile warming into a bright genuine smile with one natural blink, and holds that look. One continuous seamless shot, Generate single shot. Sharp stops contrasting with flowing movement, smooth organic motion with natural momentum, her long hair flows and settles fluidly behind her as she turns. Her face, hairstyle, skirt and jewelry remain completely consistent throughout, natural body proportions, background texture stable with no morphing and no flickering. No text, no watermark, no extra people, no clothing change, no warped limbs.

### 7.5 视频·T03 原地律动保底（降级档，动作幅度最小）
Vertical clip, fixed full-body camera, she stays centered in frame, the sunlit bedroom background remains stable and unchanged, softly blurred behind her. The young woman in the pink high-waist fine-pleated maxi skirt shifts her weight slowly onto her right hip, left knee softly bending, body settling into a relaxed S-curve, then hits a sharp confident hip pop and holds for a beat, the pleats stretching over the hip line. With hands on her waist she hits crisp shoulder pops to the beat, alternating left and right, then twists her waist slowly side to side while her shoulders stay forward, the pleats rippling like waves around her legs. Finally she tucks a strand of hair behind her ear, tilts her head, her relaxed smile warming into a bright genuine smile with one natural blink at the camera, weight on one leg, hip slightly out, and the skirt settles softly around her. One continuous seamless shot, Generate single shot. Crisp accents followed by smooth flow, feet grounded, her glossy hair strands sway gently in a light breeze. Her face, hairstyle, skirt and jewelry remain completely consistent throughout, natural body proportions, background texture stable with no morphing and no flickering. No text, no watermark, no extra people, no clothing change, no warped limbs.

## 8. 填空公式（换人/换场景/换商品套用）

**首帧八槽**：[1 来源句] [2 人物精修层+头发+饰品] [3 服装保真句] [4 中途姿态+表情] [5 机位构图句] [6 场景背景句(preset 整段)] [7 光线句(preset 整段)] [8 排除句]
- 换商品：只改槽3 的 garment 描述与参考图引用；其余不动（保人物一致）。
- 换场景：只改槽6/7（用§3 preset 整段替换）。
- 换人设：改槽2 的精修层细节（肤色/唇色/发型），保持「轻美颜」句式结构。

**视频四句**：[1 机位+背景一致性句（场景名与首帧一致）] [2 三拍动作段（§5 动词链拼装）] [3 节奏+布料响应句] [4 锁定句+Generate single shot+排除句]
- 走位类动作必须加全身锁句（T02 教训：不加则后段机位推近）。

## 9. 使用方式

### 9.1 手动流程（任意平台通用）
| 步 | 操作 | 参数/要点 |
|---|---|---|
| 1 | 拼首帧 prompt（§8 八槽） | 禁写词表§6 逐条自查 |
| 2 | 文生图 | wan2.7-image-pro：size=1080*1920；可附商品参考图（仅服装引用） |
| 3 | 目检门禁 | §9.3 清单；不过不重生成（额度纪律），先改词 |
| 4 | 拼 i2v prompt（§8 四句） | happyhorse-1.1-i2v：duration=15、1080P、9:16；**无 negative_prompt 字段**，约束全正向 |
| 5 | 图生视频 → 抽帧 QA | f2/f6/f10/f14 四帧对照§9.4 |
| 6 | 交付 | 精确 15.000s 裁切（trim 0-360 帧@24fps）+ 可选字幕烧录 |

### 9.2 本仓库一键管线
```bash
python3 scripts/video_pipeline.py init --template T01 --scene bedroom --authorize "<授权原文>" --run my-run-001
python3 scripts/video_pipeline.py image  --run my-run-001   # 生成+下载+打印门禁清单
# （人工/agent 目检通过后）
python3 scripts/video_pipeline.py approve --run my-run-001 --review-note "<目检结论>"
python3 scripts/video_pipeline.py video  --run my-run-001
python3 scripts/video_pipeline.py poll   --run my-run-001
python3 scripts/video_pipeline.py download --run my-run-001
python3 scripts/video_pipeline.py qa     --run my-run-001
DINGTALK_SELF_USER=<你的钉钉userId> MAC_SSH_TARGET=<user@host> python3 scripts/video_pipeline.py deliver --run my-run-001 --dingtalk --web --mac
```
纪律内建：授权留痕、执行器 sha 锁、未 approve 禁视频、失败不重提、poll SSL 中断续跑一次、幂等键、stale mount 自动降级 scp。

### 9.3 首帧目检清单（≥6/7 才放行）
①像手机原相机直出而非摄影作品？②人物动作中而非定格摆姿？③背景有使用痕迹且非样板间？④光线是窗光/顶光级普通光？⑤构图偏心或略歪、有前景遮挡或裁切？⑥皮肤匀净微光泽、无被强调瑕疵？⑦整体保留一个「不完美」？
附加四项：鞋入画 / 无相机器材穿帮 / 饰品≤2 件 / 商品保真（裙色、褶、腰band 与源商品一致）。

### 9.4 视频 QA 八项（抽 f2/f6/f10/f14）
三拍齐 / 裙摆因果链（动→褶响应→停→settling）/ 手指解剖 / 脚底接地 / 脸部无漂移 / 裙褶无闪烁 / 背景零扭曲 / 结尾定格+微笑渐变+一次眨眼。规格：15s（精确版 360 帧@24fps）/1080×1920。

## 10. 失败剧本（症状→根因→修词）

| 症状 | 根因 | 修复 |
|---|---|---|
| 背景扭曲/熔化 | i2v 重写了背景 | 背景只留首帧；i2v 仅一句一致性复述+locked camera+Generate single shot |
| 脸崩/五官漂移 | 特写×剧烈运动同现或脸部预算超支 | 降景别到全身/膝上；15s 只留 1 眨眼+1 微笑渐变；加锁定句 |
| 雀斑/瑕疵显得刻意 | 瑕疵特征名词被强调渲染 | 删 freckles/pores；换轻美颜精修层整段 |
| 房间像样板间 | cream wall+monstera 等造型美学 | 换生活化三信号杂物清单；略乱≠脏乱差 |
| 塑料假人感 | flawless/8K/masterpiece 等精修词 | 删精修形容词；保留来源叙事+自动曝光 |
| 后段机位推近（走位类） | 缺全身锁句 | 加 the camera keeps the same full-body distance from head to shoes throughout with no zoom-in |
| 手指崩坏 | 手部高危饰品/复杂手部动作 | 饰品≤2 件避开手部；手部动作限 tuck hair / 扶腰band / 提裙摆 |
| 视频平淡无起伏 | 弱动词+否定句+静态首帧 | 强动词链+动停对比+首帧中途姿态 |
| 结尾不收势 | 缺定格句 | 尾拍加 holds a confident final pose + smile warming into a bright genuine smile with one natural blink |

## 11. 迭代案例（v5→v6→v7，三轮用户反馈驱动）

| 改动点 | v5（刻意版） | v6（真实但素） | v7（定版） |
|---|---|---|---|
| 皮肤 | freckles+visible pores | smooth even skin, light beauty-filter finish | +gentle dewy glow+tightline+curled lashes+gradient lips（精修层） |
| 场景 | cream wall+monstera+整齐床 | rumpled 被+椅背搭衣+充电线+冰美式 | 同 v6（保留） |
| 相机词 | Fujifilm X100V+50mm+grain | phone snapshot+chest height | 同 v6（保留） |
| 鞋/穿帮 | — | 赤脚+三脚架入镜 | 补鞋句+no tripod 排除 |
| 结果 | 用户判「刻意」 | 用户判「真实但不够精致」 | 用户判「很完美」 |

**额度与授权纪律**：每次生成单独用户授权并留痕；单 run ≤2 posts（1 图+1 视频）；失败不自动重提；首帧可跨 run 复用（复用=0 图 POST）。

## 附录 A 证据源（验证等级：★★★全文核读 / ★★多源摘要一致）
万相官方 Prompt 指南与 Wan2.2-I2V 模型卡（i2v 公式/背景锚定）；happyhorse-1.1-i2v 模型页（无 negative_prompt 字段）；CSDN《AI生图如何增加真实感》★★★（来源叙事/瑕疵轻微原则/构图清单）；新浪财经《越精致越划走》★★★（真实感检查清单/毛边感）；Sprout Social UGC★★★（authenticity/relatability）；抖音美颜机制与磨皮 30-50% 共识★★；穿搭原生机位教程（胸高内倾/脚贴底边）★★；本仓 research/character-scene-v2-20260928/route-R1~R4 四路调研底稿。

## 附录 B 文件索引
| 文件 | 内容 |
|---|---|
| docs/prompt-templates-v5.json | 机读模板：keyframe_prompts(bedroom/street)、tiers[T01-T03]、禁写词表、preset |
| docs/video-motion-prompt-spec.md | 规范原文 v2.1（§9 人物/§10 场景/§11 模板升级点） |
| docs/beautiful-character-prompt-playbook-v1.md | 本手册 |
| scripts/video_pipeline.py + docs/pipeline-sop.md | 一键管线与 SOP |
| research/character-scene-v2-20260928/ | R1 妆容/R2 人物/R3 场景/R4 真实短视频审美 四路底稿 |

*手册 v1.0 · 2026-09-30 · 由七次真实生成与三路对抗审计固化；示例 prompt 与模板 JSON 逐字一致。*



# 跨境电商人物短视频生成提示词规范 v2.0（产品版）

> 2026-09-25 · 四路并行子 agent 深度调研交叉汇总（底稿见 research/dance-feel-20260925/route-A.md、route-B-part1~3.md、route-C.md、route-D.md）
> 适用链路：wan2.7-image-pro 关键帧首图 → happyhorse-1.1-i2v 15s 竖屏 9:16 单镜头（仅正向英文 prompt，无 negative_prompt 字段，duration=15，resolution=1080P）
> 商品：粉色高腰细百褶长裙 product_8822221153828

## 0. 根因诊断：为什么当前视频没有平台原生感

09-24 tokenplan-character15 run 的 video_prompt_en 存在**三重锁死**（三路独立调研交叉证实）：

1. **弱动词自我阉割**：明文写了 gentle, graceful standing sway / small comfortable movement / not energetic dancing / very shallow shoulder-line tilt——Kling 手册翻车点：gentle/sway 等字面词直接主导输出，把运动强度锁死在 Low 档（1-3/10）。
2. **否定句式反噬**：大段 no spinning, no walking, no new gestures——扩散模型对否定的已知弱点是**把被否定概念植入注意力**且遵循率不可靠；同时「双脚钉死+禁止一切大动作」让画面只剩原地微晃。
3. **静止首帧拖底**：Runway 官方 FAQ 机制——首帧的 implied motion（动作中途姿态/方向线）决定模型运动倾向；当前 keyframe 是「双脚并拢站定、双臂垂放」的完全静止 pose，i2v 端再强的动词也会被静止首帧拖低幅度。

另有一个**节拍预算错误**：15 秒只安排了 1 个动作（一次浅摇摆），而平台原生内容的节拍密度是每 2.5-4s 一个可感知变化。没有「动-停反差」就没有卡点感，没有卡点感就没有平台原生感。

## 1. 四路交叉验证结论（含冲突裁决）

| 议题 | 各路结论 | 裁决 |
|---|---|---|
| 节拍密度 | C路(Kling18实测)：15s≤3个beat；A/B/D路：4-6个动作单元 | **3 大拍（起势-主体-收尾）为骨架，每大拍内嵌 1 个次级动作，全片可感知变化 ≤5 次**。6 单元是上限不是目标（iosur 过载红线） |
| 动作强度 | C路：强动词+幅度/速度副词+明确终点；A路：动词用强副词用稳 | 一致采纳：**a sharp hip pop then holds / whips her head 式写法——动词强、副词稳、每拍有起止状态** |
| 首帧姿态 | D路：首帧即动作张量最大瞬间；C路(Kling23)：首帧不能是高潮顶点，要运动中性有势能 | **统一为「动作中途但非顶点」**：裙摆轻微扬起、重心偏单腿、身体微前倾=implied motion 线索；裙摆全开的高潮留给中段 |
| 速度感来源 | A/B/C 三路一致 | **动-停反差（sharp accents followed by smooth flow / freeze poses on the beat），不是全程快** |
| 镜头 | C路万相官方：fixed camera=静止专注；A路iosur：主体大动作与镜头大运动二选一 | **fixed full-body camera（或仅 very slight push-in），禁止 orbit>45°（万相官方畸变警告）** |
| 负面约束 | B/C/D 三路一致 | **正文全正向（质量锚正向写），末尾最小约束槽只放 no text/watermark/extra people/clothing change/warped limbs** |
| 裙摆描写 | B路：每动作配面料响应句；C路：面料-身体分离句式防穿模 | **合并采纳：每个动作 beat 配一句 the skirt swings/ripples/flares/settles，并锁定 outfit design, fabric texture unchanged** |

## 2. 动作拆解库（合并 A 路 9 族 + B 路 A1-A13，去重后 16 条）

风险档：🟢=AI 可稳定生成 🟡=需写法保护 🔴=禁用（见 §5 禁忌表）

| # | 动作 | 节拍 | 拆解要点（部位→动作） | i2v 英文短语 | 档 |
|---|---|---|---|---|---|
| M1 | 重心转移 S 曲线 Weight Shift | 2-3s | 重心压单腿→承重侧胯外弹→对侧肩沉→头微倾→膝不锁死；双脚平均受力=僵硬第一大错误 | she slowly shifts her weight onto her right hip, left knee softly bending, body settling into a relaxed S-curve, opposite shoulder dropping slightly | 🟢 |
| M2 | 顶胯定格 Hip Pop | 1.5-2.5s | 上下固定中间发力：肩稳上身垂直，胯快弹 0.5s+定格 1-2s；A 字站姿；高腰裙面料横向拉伸=卖点放大器 | a confident hip pop to the right, shoulders staying level and still, then holds; pleated skirt stretching over the hip line | 🟢 |
| M3 | 8 字摆胯 Figure-8 Hip Sway | 2-4s | Taemin MOVE「less is more」：胯 isolation 清晰、肩静止、视线锁镜头微眯；裙摆横向波浪 | she sways her hips slowly side to side in a figure-8, minimal upper body movement; the pleated skirt follows with soft waves | 🟢 |
| M4 | 扭腰摆胯 Waist Twist | 2-4s | 肩线朝前+胯转 45°=肩胯错位；腰为轴；一脚置另一脚后；百褶螺旋行波=细褶最大视觉红利 | hips angled 45 degrees from the camera while shoulders stay forward, twisting her waist slowly, pleats rippling like waves around her legs | 🟢 |
| M5 | 两步律动 Two-Step Groove | 2-3s | foolproof 万能律动=人体节拍器；侧步+并步点地+膝弹性微屈；给大动作做对比铺垫 | she grooves side to side in a relaxed two-step, bouncing lightly on the beat, gentle knee bounce | 🟢 |
| M6 | 踮脚弹胯 Swagg Bouncee | 2-3s | 前脚掌踮起轻弹+全幅度左右弹胯；make it bigger=更自信；长裙漂浮感 | bouncing lightly on her toes, hips swaying with full range of motion; the long pleated skirt swings side to side with playful energy | 🟢 |
| M7 | 肩部卡点 Shoulder Shimmy & Hit | 2-4s | ITZY Wannabe：右肩上顶左肩下压对角线交替，只动胸肩 isolation；双手叉腰展示高腰线；松紧对比=KPOP 记忆点 | hands on her waist, she hits sharp shoulder pops to the beat, alternating left and right; isolated shoulder shimmy with confident attitude | 🟢 |
| M8 | 手臂波浪 Arm Wave | 2-3s | 腕→肘→肩依次传导；手指自然伸直放松；竖屏内单臂侧波浪占满画面宽度 | a fluid arm wave ripples through her arms, from fingertips to shoulders; smooth liquid wave motion | 🟢 |
| M9 | 过顶框位 Whacking Lines & Overheads | 2-3s | 单臂下指→侧指→上指卡拍切换；双手颈后框头挺胸抬下巴；几何臂位截图传播价值强 | sharp straight arm lines hitting the beat; she frames her head with both arms, chest open, chin lifted confidently | 🟢 |
| M10 | 捞臂过顶 Scoop Arm Overhead | 3-4s | 胸前捞起→过顶划弧→向前点出→接摆胯；竖屏拉长身体线条；二段式自带小高潮 | she scoops one arm across her chest and sweeps it gracefully overhead, then points forward, flowing into a relaxed hip sway | 🟢 |
| M11 | 猫步走近 Sassy Walk | 2-3s | 视线锁镜头+每步送胯（hip-led）+直线脚位；「她朝你走来」=打破第四面墙标准钩子；走路是 i2v 最稳定动作之一 | she walks confidently toward the camera in a straight line, hips leading each step; the skirt sways with each step | 🟢 |
| M12 | 急停惯性 Abrupt Stop | 0.5-1s | 重心脚钉住+发丝裙摆惯性前荡再回落=「真实物理」最强信号，观众潜意识识别为高级感 | she stops abruptly, feet planted, momentum carrying her hair and skirt forward before settling | 🟡（写清终止态） |
| M13 | 慢速单圈转身 Slow Single Turn | 3-4s | 裙装带货 money shot：一臂 overhead 为轴、前脚掌 pivot、匀速 360° 禁多圈；裙摆离心开花→惯性余摆→垂落三阶段=单镜头内小型叙事 | she performs one slow graceful turn on the balls of her feet, one arm raised overhead; the pleated skirt flares outward in a smooth arc, then settles softly as she faces the camera | 🟡（全片≤1次） |
| M14 | 提裙撩摆 Hem Lift & Sway | 1.5-4s | 双手轻提裙摆两侧边缘手指轻捏不攥紧；少女感/仙气标签与粉色百褶人设匹配；手部写整体姿态禁手指级细节 | both hands gently lifting the sides of her pleated skirt; she sways the skirt hem with her hands, fabric flowing like waves | 🟡（手指风险） |
| M15 | 留头回眸 Over-Shoulder Look | 2-3s | 身体先转→肩转→头最后转回（留头=T台核心技术，抖音教学 23.3 万赞）；背对→回眸信息差=钩子结构 | she turns her body away, then glances back over her shoulder, head turning last, eyes meeting the camera with a soft confident smile | 🟢 |
| M16 | 甩发+撩发定格 Hair Flip / Tuck & Pose | 1-2.5s | 甩发 1-1.5s 全片最快爆点（甩前反向微沉蓄力→水平弧线快甩→视线锁镜头）；撩发别耳后+歪头 wink=结尾定点杀，最后 2 秒决定完播/重播/截图 | she whips her head to the side, long hair flipping through the air in a wide arc / she slowly tucks a strand of hair behind her ear, final pose with weight on one leg, hip slightly out, playful wink | 🟡（甩发≤2次，遮脸风险） |

**手部填充拍**（主动作之间缝合用，1-2s）：fingertips resting lightly on her waistband, elbow angled out（指尖轻搭非整掌压）/ one hand running loosely through her hair / fingers lightly touching her collar without pressing。禁忌：手指大幅张开、手掌平压身体、手臂直指镜头（foreshortening）、双手藏身后、无目的乱摸。

## 3. 15s 三档成品模板（可直接填入 execution-release.json）

> 通用规则：3 大拍骨架（起势→主体→收尾定格），每拍写清起止状态；动词强、副词稳；每拍配裙摆面料响应句；正文全正向，末尾最小约束槽；总长 80-160 词；固定全身机位（大幅动作预算全给主体，Kling 算力分配原则）。

### 档位 1「全身律动展示」（首选：优雅+裙摆开花 money shot，中低风险）
动作映射：M5→M3→M8/M9→M13→M16（5 变化点，3 大拍）

video_prompt_en:
```
Vertical handheld vlog-style clip, fixed full-body camera. The young woman in the pink high-waist fine-pleated maxi skirt grooves in a relaxed two-step, bouncing lightly on the beat, then flows into a slow figure-8 hip sway, the pleats rippling like soft waves around her legs. She sweeps one arm in a fluid wave and frames her head with both arms overhead, chest open, chin lifted, then performs one slow graceful turn on the balls of her feet, the skirt flaring outward in a full circle, pleats fanning open. Finally she faces the camera as the skirt settles softly, tucks a strand of hair behind her ear and holds a confident final pose, weight on one leg, hip slightly out, warm smile, direct eye contact. One continuous seamless shot, crisp accents followed by smooth flow, smooth organic motion with natural momentum, face stable, body proportions consistent, outfit design and fabric texture unchanged, feet grounded. No text, no watermark, no extra people, no clothing change, no warped limbs.
```

### 档位 2「走位互动展示」（最强平台原生感：走位+急停惯性+回眸，中风险）
动作映射：M11→M12→M2→M13→M15（动-停反差最大化，适配 BGM 重拍后期卡点）

video_prompt_en:
```
Vertical handheld vlog-style clip, fixed full-body camera. The young woman in the pink high-waist fine-pleated maxi skirt walks confidently toward the camera in a straight line, hips leading each step, the skirt hem swaying with every step, then stops abruptly, feet planted, momentum carrying her hair and skirt forward before settling. She holds a sharp confident hip pop in an A-line stance, fingertips resting lightly on her waistband, then lifts the sides of her skirt with both hands and performs one slow graceful turn, the pleats fanning open in a full circle. The turn ends with her back to the camera, the skirt settling softly, and she glances back over her shoulder, head turning last, eyes meeting the lens with a soft confident smile, and holds that look. One continuous seamless shot, sharp stops contrasting with flowing movement, smooth organic motion with natural momentum, face stable, body proportions consistent, outfit and fabric texture unchanged. No text, no watermark, no extra people, no clothing change, no warped limbs.
```

### 档位 3「原地律动保底」（原地律动：无转身无走位，模型反复崩坏时用）
动作映射：M1→M2→M7→M4→M16（双脚原地，仍保留 4 个卡点切换与动-停反差）

video_prompt_en:
```
Vertical clip, fixed full-body camera, she stays centered in frame. The young woman in the pink high-waist fine-pleated maxi skirt shifts her weight slowly onto her right hip, left knee softly bending, body settling into a relaxed S-curve, then hits a sharp confident hip pop and holds for a beat, the pleats stretching over the hip line. With hands on her waist she hits crisp shoulder pops to the beat, alternating left and right, then twists her waist slowly side to side while her shoulders stay forward, the pleats rippling like waves around her legs. Finally she tucks a strand of hair behind her ear, tilts her head with a playful smile at the camera, weight on one leg, hip slightly out, and the skirt settles softly around her. One continuous seamless shot, crisp accents followed by smooth flow, feet grounded, face stable, body proportions consistent, outfit and fabric texture unchanged. No text, no watermark, no extra people, no clothing change, no warped limbs.
```

## 4. 首帧 keyframe prompt 修改（wan2.7-image-pro）

旧版首帧问题：both feet planted and weight centered, arms relaxed outside the skirt = 完全静止对称 pose，锁死 i2v 运动倾向（Runway implied motion 机制）。

**修改点**（保留原有全部商品保真/人物/合规约束，只改姿态与构图段）：
1. 姿态改为「动作中途但非顶点」：重心落单腿、另一膝微屈、自然小步位（双脚不并拢锁死）、胯微侧弹出、躯干呈放松 S 曲线；
2. 埋 implied motion 线索：裙摆捕捉在轻微扬起/摆动中途（caught mid-sway, hem lifting slightly on one side）、发丝微动；
3. 手要忙：一手指尖轻搭腰 band 肘部外展，或一手松散抚发（不攥不压）；
4. Lead room：人物略偏画面一侧，面朝/视线朝向留白侧，给后续走位与转身留空间；
5. 全身中远景：头顶与脚下留余量，人物占画面高度约 2/3-3/4（大幅舞蹈动作预算下不要近景）。

替换句式（插入原 keyframe prompt 的姿态段）：
```
Pose her with motion-ready energy: weight pressed onto one leg, the other knee softly bent in a natural small step, hip popped slightly to the side, torso in a relaxed S-curve, the skirt hem caught mid-sway lifting slightly on one side as if she just shifted her weight. One hand rests with fingertips lightly on her waistband, elbow angled out; the other arm hangs relaxed. She stands slightly off-center with open space on the side she faces, looking toward the camera with a warm confident smile. Full-body medium-wide framing with headroom and floor space, subject occupying about three quarters of image height.
```
（注意：档位 2 猫步流如要「从纵深处走来」，首帧人物可稍退远、留更多地面空间；档位 1/3 通用上述姿态。）

## 5. 写法禁忌速查（生成前 checklist）

**禁写词**（每词对应崩坏点）：jump / leap / fast spin / multiple turns / pirouette / drop to floor / floor work / touch knee / grab the skirt tightly / whip hair（连甩） / rapid footwork / high kick / each finger pinching（手指级细节） / dynamic / epic / 8K / masterpiece（空词稀释注意力）。
**禁写结构**：否定式约束散在正文（no/not/without 遵循率不可靠且植入概念）；gentle/subtle/small comfortable movement（强度锁死词）；主体大动作+镜头大运动同时；一个维度两个值（两个速度档/两个运镜方向）；6 个以上动作单元。
**必写项**：每拍起止状态（starts/then/finally + holds）；每动作一个速度副词；每拍一句裙摆响应（swings/ripples/flares/settles）；One continuous seamless shot；末尾正向质量锚（face stable, body proportions consistent, outfit and fabric texture unchanged, feet grounded）+ 最小约束槽（no text, no watermark, no extra people, no clothing change, no warped limbs）。
**后期层（不要写进 prompt）**：字幕/贴纸（带字幕广告好感+95%但必须剪辑层加）、BGM 卡点与变速（i2v 无音乐概念）、跳切/punch-in。

**生成后验收清单**：①动作完成度（3 大拍是否都出现，有无压成闪帧）②裙摆物理（开花→余摆→垂落因果链）③手指计数与自然度 ④脚底是否打滑 ⑤面部是否漂移/身份一致 ⑥百褶纹理是否闪烁、裙长颜色是否漂移 ⑦是否有穿模（腿-裙交叉区）⑧结尾是否定格在镜头前。崩坏则按档位降级：1→2 或 →3；同档重生成最多 1 次，不无限重试。

## 6. 平台原生感机制要点（为什么这样改会有平台原生感）

1. **第一帧即动作**（HubSpot "start with action" + Wistia 留存曲线开头 2% 跳水）：首帧裙摆已在摆动中途，开场即是律动而非起步铺垫。
2. **动-停反差 = 无 BGM 的卡点感**：sharp accents followed by smooth flow / freeze poses；每拍结尾 hold 0.5s，后期配 BGM 重拍即天然卡点。
3. **对镜互动**（PSI 准社交机制，Gen Z 购买意愿经 PSI 中介）：全程 direct eye contact + 结尾 wink/微笑 = 「她对你一个人展示」。
4. **面料动势 = 产品证明**（Shopify context 逻辑）：百褶裙的卖点只有运动能证明——裙摆开花就是「想要这条裙子」的瞬间。
5. **UGC 质感**（含 UGC 帖子转化率 10 倍+，Emplifi）：handheld vlog-style、真实生活场景光、candid 能量，而非 studio commercial 质感。
6. **15s 目标 = 100% 完播 + 复看**：结尾定格与开头动势可无缝循环。

## 7. 来源与验证等级汇总

| 等级 | 来源 |
|---|---|
| 官方一手 ✅ | 阿里云万相 Prompt 指南（中/英）、万相 3.0 指南（音频驱动舞蹈 9:16 同构模板、环绕≤45°警告）、Runway Academy Gen-4.5（i2v 句式、首帧 implied motion FAQ、positive phrasing）、HappyHorse 官方（15B/1080P/3-15s/音画联合） |
| 数据实证 ✅ | Shopify UGC（Emplifi 10x/Bazaarvoice 65%/PowerReviews 95%）、HubSpot 视频营销（start with action、字幕+95%）、Wistia 1300 万视频（<1min engagement 52%、平均观看 16s、留存 nose 跳水）、Sprout Social（TikTok 最佳 21-34s、lo-fi authenticity）、Semantic Scholar PSI×Gen Z 购买意愿 4 篇 |
| 专业教程全文 ✅ | STEEZY 9 篇（MOVE 摆胯/Wannabe 肩 hit/Mic Drop 滑步/Two-Step/Swagg Bouncee/Whacking/Popping/How To Dance Sexy/拍摄 5 要点）、MintedModels、Ken Jones NYC、Shotkit、ExpertPhotography、iosur AI 视频故障手册、Higgsfield 防畸变指南、太平洋摄影部落、百家号/搜狐/新浪姿势文、360kuai |
| 社区手册 🔶 | GitHub kling-prompt-engineering（02/04/09/10/11/15/18/19/23 章，15s≤3beat 量化结论出处）、cliprise awesome-image-to-video-prompts、freeaitool 三篇、CSDN Seedance 活人感提示词/TikTok 舞蹈全解析 |
| 仅搜索摘要 ⚠️ | 抖音留头教学(23.3万赞)/布机道对镜自拍(253.9万赞)/侧身回头杀/送胯教程、头条提裙转圈/321 抓拍、微信公号摆胯训练、B站回眸 |
| 不可达 ❌ | 可灵/海螺/Vidu/Pika 官方指南、TikTok Creative Center 一手、dylaninthedetails/jessicawhitaker、知乎/Reddit |

**未验证项处置**：节拍密度定量研究、滑步官方条目、重心脚位官方文档、「平台原生感」中文一手拆解文均未获得——相关结论已标注为推断/常识，落地以 A/B 实测为准（同首帧下档位 1 vs 旧版对照各生成一次）。

---


---

## 8. A/B 实测增补（2026-09-25 22:0x-23:0x，Token Plan 真跑）

| 项 | 模板T01 全身律动展示 | 模板T02 走位互动展示 |
|---|---|---|
| 运行目录 | build/tokenplan-dance-20260925 | build/tokenplan-dance2-20260925（复用模板T01首帧，变量唯一） |
| 成片 | 13.0MB / 361帧 / 15.04s | 15.8MB / 361帧 / 15.04s |
| 开头（0-3s） | two-step+摆胯起势，裙摆即动 | ✅ 走位逼近镜头，步态+裙摆摆动+发丝微动，开场压迫感更强 |
| 中段 | ✅ 转身裙摆扇形开花（money shot 达成） | 提裙转身达成，裙摆开花 |
| 结尾（12-15s） | ✅ 全身入画撩发定格，产品hero保留 | ❌ 机位漂移到腰上近景，裙子出画——违反全身锁定，结尾产品丢失 |
| 身份/服装一致性 | ✅ | ✅（面部质量甚至更锐） |
| 用户验收 | 「很完美」 | 待对照 |

**结论与修订（v1.1）**：
1. 模板T01 保持主模板地位。
2. 模板T02 的走位开场值得吸收，但必须加**全身锁定句**防机位漂移：在 Camera 段追加 "the camera keeps the same full-body distance from head to shoes throughout, no zoom-in, she stays fully in frame"；走位限 2 步（walk 越长漂移概率越高）。
3. 混合模板（下次迭代候选）：模板T02 的 0-4s 走位+急停开头 + 模板T01 的中段转身开花与结尾全身定格 + 全身锁定句。
4. 实测再次验证 §1 裁决：单镜头 i2v 的机位漂移是「走位类」动作的主要失败模式，全身锁定句应列为走位类模板的必写项（已并入 §5 必写项）。


## 9. 人物规格 v2（首帧阶段写入，视频段只留锁定句）

### 9.1 妆容五粒度（总 25-35 词，按 skin→blush→lip→brow→eye 各 1 短语）
| 风格 | 适用 | 核心 EN 短语 |
|---|---|---|
| clean girl（粉裙卧室首选） | 邻家/晨间 | natural skin texture with a healthy glow / soft peach blush on the apples of her cheeks / sheer glossy nude-pink lips / natural fluffy brows / thin brown eyeliner and curled lashes |
| glass skin | 韩系精致/特写 | dewy glass skin, luminous well-moisturized finish / gradient tinted glossy lips |
| latte 拿铁妆 | 街边暖调 | monochromatic muted coffee eyeshadow / warm bronzy blush / lips lined in soft brown topped with clear gloss |
| glazed | 近景高级感 | glazed glowy skin / subtle highlighter shimmer on cheekbones（进 i2v 动作须小） |
禁用：flawless / porcelain / airbrushed / beauty filter / soft-focus skin / 8K / masterpiece（塑料感与遗产词）。
反塑料必写：unfiltered skin, visible pores, peach fuzz catching window light, faint under-eye texture, light freckles across the nose（每角色 ≥2 个瑕疵）；相机锚定 Fujifilm X100V look, light film grain。

### 9.2 饰品（全身镜头 ≤2 件）
安全区：small gold hoop earrings + a delicate gold pendant necklace at her collarbone；加件限 pearl hair clip / flower tucked behind her ear / slim headband。
禁区（手部=万相官方 negative 点名高危区）：戒指、多层细项链、叠戴手镯、摇曳耳坠、美甲细节、肩背包、品牌 logo/文字饰品。材质 gold/pearl 优于 silver/rhinestone。

### 9.3 发型与身材脸部
发型：long silky black hair middle-parted with a few loose strands（卧室）/ sleek low ballet bun（街边 latte）；动态句用官方直译 her glossy hair strands sway gently in a light breeze；禁 hair flying wildly（与百褶动模糊叠加）。
身材：natural body proportions + slender, naturally toned build + graceful upright posture + about 168cm, healthy weight；腿长用服装结构表达（high waistline elongating the legs）。禁 sexy/curvy/busty/tiny waist/supermodel body/skinny（限流+畸变双风险）。
脸部：delicate facial features；微笑分级 relaxed confident smile → bright genuine smile with slightly crinkled eyes（渐变式）；眨眼只写 one natural blink；眼神 eyes with moist light reflection。

### 9.4 距离-脸崩预算
全身镜头脸=氛围级：皮肤/妆容词在首帧渲染生效，视频段只留锁定句；knee-up=脸表演级平衡带（如需近景资产单独生成+锁定镜头）；近景×剧烈运动禁止同段；15s 脸部预算=1 眨眼+1 微笑渐变。

## 10. 场景规格 v2（背景只写进首帧，i2v 仅一致性句）

### 10.1 官方公式（万相）
i2v prompt = 运动 + 运镜；背景由首帧锚定，i2v 重写背景=冲突→重绘扭曲（背景错乱根因）。i2v 仅允许一句一致性复述 + locked camera + Generate single shot.

### 10.2 三场景 preset（背景段/光线段用于首帧 image prompt）
A 阳光卧室（首选）：背景 A cozy sunlit bedroom. A neatly made bed with white linen and one rumpled corner sits near a large window; sheer pale-beige curtains diffuse the morning light. A potted monstera stands in the corner softly blurred, a wooden nightstand holds a folded blanket, soft cream wall. 光线 Soft natural window light from camera left, warm morning tone, low contrast, gentle rim light on the figure.
B 咖啡店室内（备选）：背景 A cozy café interior. A wooden table with a ceramic coffee cup anchors the foreground; blurred shelves of cups, a chalkboard menu, and warm pendant lights recede behind. A leafy potted plant sits by a foggy window. 光线 Warm mixed light: soft window daylight plus low pendant lamp glow, low contrast, warm tone.（吊灯写 static pendant lights）
C 城市街边（谨慎）：背景 A city sidewalk beside a boutique café storefront. Blurred pedestrians and slow-moving traffic form a soft background; a green planter box and a striped awning anchor the foreground, a brick wall and distant crosswalk recede behind. 光线 Soft overcast daylight, low saturation, flat even lighting, no harsh shadows.（人车必须 blurred/out of focus、不写数量、招牌 illegible）
稳定性排序：咖啡店≈卧室<街边；真实感排序相反。杂物 3-5 件为限；床/镜/桌椅放画面边缘或虚化；镜面写 reflection blurred。

### 10.3 背景稳定性十条
1 locked/static/fixed camera（官方）2 Generate single shot.（官方）3 i2v 不重写背景（官方公式）4 Blurred … forms the background + out of focus（Wan2.2 官方示例）5 运动用 slowly/gently 程度副词 6 禁环绕/快速平移/穿越运镜 7 背景多软材质少硬几何 8 镜面/玻璃 reflection blurred / foggy glass 9 prompt_extend 慎用 10 负面全正向末尾：background stays stable and consistent, no morphing, no flickering textures。

### 10.4 配色
衬粉裙：cream/ivory 墙、warm wood、navy/raisin 深蓝、muted sage 绿、golden hour 暖调。禁：纯灰（现棚拍，用户已否）、正红、荧光绿/亮黄、冷青蓝/冷紫、黑白高对比网格。

### 10.5 首帧-场景衔接七条
背景首帧写定 i2v 只复述；9:16 一致；背景元素靠边让运动空间；首帧埋 implied motion；光线方向首帧=i2v 不得改；杂物 3-5 件；prompt_extend 关。

## 11. 模板 v5 升级点（见 prompt-templates-v5.json）
1 新 keyframe_prompt_v2：人物全规格（9.1-9.3）+ 卧室场景（10.2A）+ mid-motion 姿态 + 50mm 相机锚定；街边版=替换场景句+latte 妆+ballet bun。
2 T01-T03 video prompt 增：背景一致性句（the sunlit bedroom background remains stable and unchanged, softly blurred behind her）+ 扩展锁定句（her face, hairstyle, skirt and jewelry remain completely consistent throughout）+ Generate single shot.；运动文本继承 v5 不变。
3 脸部预算落地：结尾定格段给 1 微笑渐变+1 眨眼，其余段不写脸部动作。

*v2.1 · 2026-09-28 · 人物规格+场景规格+背景稳定性整合（R1/R2/R3 三路调研）；底稿：research/dance-feel-20260925/* + research/character-scene-v2-20260928/*

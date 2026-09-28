# 电商视频叙事结构 v2（30s 五beat H-C-R-P-C）

> 适用：跨境电商listing主视频（AliExpress 类）+ 品牌社媒切片。
> 证据来源：Shopify《Product Videos: 10 Best Practices and Examples》(2023-06-28, https://www.shopify.com/blog/product-video ，2026-09-23 抓取)：五要素=Hook/Clear messaging/Solution to a pain point/(demonstration)/(CTA)；最佳实践含"sweet spot 30–60s"、detail-rich subtitles/captions、pace & tone、CTA；Wyzowl 数据（转引）：89% 消费者因视频产生购买、96% 看过解释型视频。境外脚本框架共识：Hook-Story-Offer / PAS(Pain-Agitate-Solve) / BAB(Before-After-Bridge)；短视频"黄金3秒"钩子法则。子agent深度调研（viral钩子/境外案例）回报后并入附录。

## 结构总表（30.0s）

| Beat | 时间 | 叙事职能 | 画面/运镜 | 首帧→尾帧 | 字幕(EN) |
|---|---|---|---|---|---|
| B1 HOOK | 0–4s | 图案中断+材质悬念：褶裥充满画幅摆动，快速推近 | 微距macro，push-in | detail_3 → detail_3 | Pleats that move like water. |
| B2 CONTEXT | 4–10s | 痛点/场景共鸣：通勤-周末一套搞定的生活瞬间 | 场景内入画/缓移 | detail_4 → detail_4 | One skirt, office to weekend. |
| B3 REVEAL+DEMO | 10–19s | 产品揭示+动态证明：白底平铺切到上身行走，摆幅/垂感即证明 | 平铺→行走match cut，跟移 | main → detail_1 | High waist. Full swing. Ankle length. |
| B4 PROOF | 19–25s | 细节证据：腰头缝线+褶裥 crisp 结构微距 | macro 缓移 | detail_2 → detail_2 | Crisp pleats. Clean waistband. No stretch needed. |
| B5 CTA | 25–30s | 收尾召唤：无人全貌居中，缓zoom-out到静态hold | zoom-out → static | detail_5 → detail_5 | Your everyday maxi. S–XL. |

## 规则

- 事实纪律：字幕只允许源数据可证事实（高腰/百褶/长裙及踝/无弹/涤纶/ S–XL/粉色）；比喻句不携带参数性宣称。
- 节奏：每beat内用运镜（push/track/zoom）制造≤3s的感知切分；beat间硬切，B3内用match cut（褶线对齐）。
- 合规：无水印/logo/促销贴纸；字幕白字黑描边底部；BGM -20 LUFS（无配音）；结尾无logo纯产品hold。
- 市场适配：US/KR/BR 共用无文字依赖的画面叙事；字幕仅EN（listing语言），KR/BR由文案承载。
- 生成映射：hailuo-h3-shouweizhen @1080P，durations=[4,6,9,6,5]，首尾帧链=上表；出片略长于请求（~+4%），拼接后截尾对齐30.0s。

## 与 v1 分镜（方案B）的差异

- v1 按"镜头清单"组织（Hook/Problem/Product/Proof/CTA 但首帧混用 worn 图），B2/B3 叙事弱、CTA 曾出 POV 穿视。
- v2 按"叙事职能"组织：B2 明确痛点共鸣、B3 合并揭示+动态证明（平铺→上身 match cut）、B5 强制无人居中 hold；每beat首尾帧锁定槽位门禁图，杜绝场景漂移。

## 附录A · 调研回报（2026-09-23，两路并行子agent + Mac 出口直抓）

### A1 境外 DTC 框架与案例
- 框架族：PAS（copyblogger.com/problem-agitate-solve）、BAB 与 Feature-Benefit-Outcome 与 UGC 证言弧（adcreative.ai/post/6-ad-creative-examples-that-actually-convert、adcreative.ai/post/ecommerce-product-video-frameworks-that-drive-conversions）、Hook-Story-Offer（clickfunnels.com/blog/hook-story-offer）。
- 时长共识：核心信息前置、总量 15–30s（adcreative.ai/product-video-advertising-examples-that-convert）；Amazon OLV 规格 6–120s、推荐 6/15/20/30/60s、≤500MB、16:9 与 9:16、overlay 不得遮主商品（advertising.amazon.com/resources/ad-specs/dsp/video/online-video-ads）。
- 钩子五型+原文例句（later.com/blog/scroll-stopping-content）：curiosity gap "The thing no one tells you about…"、contrarian "Posting daily isn't why you're not growing."、mid-action story、how-to、social proof；Buffer 补 question/shock-stat/listicle/FOMO（buffer.com/free-tools/hook-generator）。
- 案例拆解：Skims「Fairy Butt Mother」= 共鸣挫折→魔法转变→benefit-first（adweek.com）；Shein = 具体指令式 CTA "do stuff now"、6× 同行投放量（modernretail.co）。

### A2 短视频 viral 机制与跨境实践
- 黄金窗口 0.5–3s；钩子族=问题/冲突前置、视觉锚点（反常机位/夸张对比/打破第四墙）、curiosity gap；抖音黄金3秒模板原文："带货视频开头黄金3秒转场模板…商品的整体和细节特写镜头、使用场景镜头"（douyin.com/video/7308204836636429608）；连连跨境：mobile 注意力≈8s（global.lianlianpay.com/article/MTU4NjM4LGNhMg.html）。
- 留存复核口径=前三秒留存+Average Watch Time+Completion Rate（blog.csdn.net/wuduitech/163505238）；Socialinsider H1-2026 TikTok ER 3.85%、"tight editing, faster pacing"（socialinsider.io/blog/tiktok-benchmarks）。
- <30s 弧：开场冲突 0–3s → 中段解决+产品 15–25s → 结尾推 CTA（jianshu.com/p/9a6a055f222c）；TikTok Shop 五型结构+拆解清单（blog.csdn.net/2601_96774916/164033592）。
- 服饰证明beat原文："站姿拍全身出版型，坐姿拍半身出气质，特写拍面料出质感"（douyin.com/video/7214433418132737340）；转圈/摆幅转场（douyin.com/shipin/7484085701378803746）。
- CTA/音乐：先给价值再给品牌、无声也能读懂的叙事（动态字幕）（lianlianpay 同上）；AliExpress 主图视频规格 30–45s、≤100MB（lianlianpay.com/article/MTIyOTc5LGIwOA.html）。
- NOT VERIFIED（网关封锁未能核实，禁止引用为事实）：平均镜头长度/match cut/速度斜坡的具体数值；-14…-20 LUFS 官方出处；AliExpress rulechannel 原文。

### A3 与 v2 结构的映射
- B1 macro 钩子 = 抖音"细节特写"+ curiosity gap；B3 摆幅/转圈 = 服饰动态证明；B4 = "特写拍面料出质感"；字幕全程 = 无声可读叙事；B5 无 logo end-card = 先价值后品牌；30s 落在 AliExpress 30–45s 规格内；15s 竖版切片对应 Amazon 推荐 15s 与 TikTok 钩子窗口（9:16 合规）。

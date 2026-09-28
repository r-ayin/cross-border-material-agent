【D路报告】短视频「网感」机制研究（时尚/带货 × 15s i2v 单镜头）

== 0 网络通道 ==
可用：web_fetch直连 Shopify/HubSpot/Wistia/Sprout Social/Semantic Scholar API。失效：web_search噪音不可用；DDG/Mojeek/百度/搜狗/Bing中国区不可用；TikTok官方域不可达（经HubSpot二手转引）；Later正文截断；Nosto 403。中文一手「网感拆解」文章零获取，中文侧全部标未验证。

== 1 网感要素清单 ==
①UGC/lo-fi真实质感：Emplifi Q3-2025含UGC帖子转化率10倍+；Bazaarvoice 65%美国消费者购买决策依赖UGC；PowerReviews 95%常看评价内容、缺社会证明1/4购物者离开（均转引自 shopify.com/blog/user-generated-content）。Sprout：TikTok关键词=lo-fi authenticity+trend participation，商业视频最佳21-34s（sproutsocial.com/insights/tiktok-marketing/）。「像广告片会死」因果链=推断/未验证。
 落地prompt: shot on smartphone, vertical handheld vlog footage, natural window light, real apartment bedroom or city street background, slightly imperfect casual framing, candid documentary feel；避免 studio lighting/professional cinematic/commercial shoot（正向模型下这些词推向广告片质感）。后期：手机UI元素/贴纸。
②第一帧即动作：HubSpot原文 Start with action to grab attention / get into content quickly（blog.hubspot.com/marketing/video-marketing）。Wistia 1300万视频：<1min平均engagement 52%；留存曲线开头2%即跳水(nose)；<1min平均观看仅16s（wistia.com/blog/optimal-video-length, /understanding-audience-retention, hubspot statistics页）。
 落地：最强动作放第一句+进行时态：she is already mid-twirl as the video begins, skirt flaring outward, hair in motion；首图(wan2.7)就应选动作张量最大瞬间（裙摆飞扬/转身过半）而非站定pose。i2v链路最该吃到的红利。
③对镜互动/准社交眼神：PSI研究2024《Power of Parasocial Interaction》Gen Z购买意愿经PSI中介（semanticscholar 37b8c78c…）；2025《PSI and Gen Z purchase intention on TikTok》时尚趋势（ca4e3f10…）；眼神接触行为效应2025两篇（822113f9…, 7d22a48d…）。量化提升数据未验证。
 落地prompt: she looks directly into the camera lens, makes eye contact with the viewer, smiles and mouths a silent greeting, playful knowing glance；glances between camera and dress hem（行业惯例未验证）。
④动作节拍密度：锚点已验证（21-34s最佳、头部发布者<30s、平均观看16s、留存开头跳水）；逐秒节拍定量研究未验证。工程化外推：15s内4-6个动作节拍（每2.5-4s一个可感知变化：动作/朝向/相机距离至少变其一）。单镜头节拍三来源优先级：主体动作切换 > 相机运动变化 > 速度变化。变速卡点留后期。
⑤服装动态表现力：百褶裙卖点（褶裥律动/垂坠/展开面积）只有运动才能证明，静止站姿=没展示产品（Shopify context逻辑已验证，运动vs静态定量对比未验证）。
 落地prompt: pleated fabric sways and flares with every step, skirt catches air mid-spin, hem lifts dynamically。当前视频病根=prompt明文锁死gentle standing sway禁spinning/walking，把②④⑤全部反向优化掉。
⑥生活化场景：real place vs staged studio（Shopify/PowerReviews）。prompt+首图: casual sunlit bedroom / city sidewalk café / full-length mirror selfie setup；与listing白底主图是两套素材不冲突。
⑦无声可看+字幕：HubSpot无声自动播放设计；TikTok带字幕广告好感+95%记忆+58%独特+25%（转引）。字幕必须后期，i2v画字必崩。

== 2 开头3秒动作设计 ==
✅(原则已验证)：1 mid-action cold open首帧即裙摆飞扬/转身过半；2 快速逼近镜头step/lean toward camera。
⚠️(行业惯例)：3 对镜直视+挑眉微笑；4 抛/甩/提裙摆大幅面料动作；5 crash zoom/quick push-in相机动势；6 before/after悬念（15s单镜头有风险）；7 文字钩子（后期层）。

== 3 节奏设计 ==
15s目标=100%完播+复看(rewatch)；结构模板：0-3s最强钩子（twirl/逼近）→3-9s产品证据（提摆/侧走/面料荡开）→9-13s互动（看镜头/指裙摆/笑）→13-15s记忆点收尾（回眸/裙摆定格飞扬），收尾与开头可无缝循环刺激复看（loop=行业惯例未验证）。

== 4 i2v prompt转译 ==
A真能表达：UGC质感/生活场景/第一帧即动作/对镜互动/then-序列显式时序（happyhorse遵循度需实测）/面料动势/相机动势（未验证）/能量词汇（需实测）。
B写了没用甚至有害：jump cut、multiple angles（诱导诡异突变）；speed ramp、beat sync（i2v无音乐概念）；text overlay/captions（画字必崩）；音乐音效。
C负面约束：末尾追加avoid static standing pose有把X引入画面风险（扩散模型否定弱点）——更稳妥=全程只写想要的（dynamic/energetic/large amplitude），两种写法A/B实测。新prompt必须删除一切gentle/subtle/graceful standing类词（拉回保守分布）。
D 15s骨架示例：Vertical 9:16 handheld smartphone vlog footage, candid lo-fi authentic style, natural golden-hour light in a real sunlit apartment. A young woman in a pink high-waisted fine-pleated maxi skirt is already mid-twirl as the video begins, pleated fabric flaring and catching air. She spins once, then steps energetically toward the camera making direct eye contact and smiling at the viewer, lifts the hem with both hands to show the flowing pleats, turns sideways and walks two quick steps letting the skirt sway dynamically, then looks back over her shoulder with a playful smile as the hem settles. Continuous lively motion throughout, upbeat fashion-tiktok energy, slightly shaky handheld camera with a quick push-in as she approaches.

== 5 来源 ==
shopify.com/blog/user-generated-content; blog.hubspot.com/marketing/video-marketing; blog.hubspot.com/marketing/video-marketing-statistics; wistia.com/blog/optimal-video-length; wistia.com/blog/understanding-audience-retention; sproutsocial.com/insights/tiktok-marketing/; semanticscholar 4篇; later.com 15-second-sales-funnel（存在未读全文）。
明确未验证不用作结论：Facebook 3秒65%说法；TikTok hook rate≥30%基准；speed ramp定量影响；中文网感拆解全部论点。

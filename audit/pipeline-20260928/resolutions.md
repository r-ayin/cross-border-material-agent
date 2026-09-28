# 审计处置记录（2026-09-28 三路对抗审计）
| Finding | 级别 | 处置 |
|---|---|---|
| A1-HIGH-01 poll续跑死代码 | high | 已修：gen(allow=(1,)) 放行 rc=1，cmd_poll 续跑一次生效 |
| A1-MED-01 sha仅init校验 | medium | 已修：gen() 每阶段复核 run 目录执行器 sha |
| A1-MED-02 send-status未实现 | medium | 已修：deliver 解析 openTaskId 并查回执 |
| A1-LOW-01 SOP 361帧笔误 | low | 已修：SOP 改 ≥360帧 |
| A1-LOW-02 模板别名/StopIteration | low | 已修：T01-T03 别名映射+不存在即 die |
| A1-LOW-03 download后不校验PNG | low | 已修：缺失即 die |
| A1-LOW-04 approve不校验sha | low | 已修：磁盘 sha 与 state 比对，缺失/不一致拒绝 |
| A1-LOW-05 清单缺商品保真 | low | 已修：GATE 清单补商品保真项 |
| A1-INFO-01 商品维度固定 | low | 接受：SOP 已知局限记载（vendor PRODUCT_FILE 硬编码） |
| A1 移交 --run 注入面 | low | 已修：run_dir+cmd_init 双重字符集校验 |
| A2-F1 跟踪文件含长效预签名URL | medium | 接受+披露：数据集为组织方公开分发、签名不含SecretKey、GitHub私仓；README 补来源声明 |
| A2-F2 --yes 收件人范围 | low | 已修：SOP 记载收件人硬编码本人单聊 |
| A2-F3 ECS公网代理零记载 | low | 已修：SOP 新增公网入口节（token 机制/链路/轮换） |
| A2-F4 gitignore 单路径 | low | 已修：通配 download_bundle.zip |
| A2-F5 R4 未提交 | low | 已于 344b138 提交（与 A3-F6 同） |
| A3-F1(meta 1080×1080) | medium | 已修 344b138 |
| A3-F2(R4/通配引用) | medium | 已修 344b138 |
| A3-F3 cafe note | low | 已修 344b138（keyframe_prompts_note） |
| A3-F4 v4 孤儿 | low | 已修 344b138（git rm） |
| A3-F5 spec 残留 v4 提及 | low | 已修 344b138 |
| A3-F2(high) 公网直链404 | high(误报) | 证伪：公网入口=ECS token 链（复测 200）；github 私仓不可公开访问系参赛素材设计；审计口径误解 |

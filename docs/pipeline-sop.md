# 15s 人物短视频生成管线 SOP（通用化流程 v1.0）

> 2026-09-28 由 09-25~09-28 五次真实运行（tokenplan-character15 / dance / dance2 / v5 / v6key / v7key / v7video）固化。执行器：scripts/video_pipeline.py（包装 sha 锁定的 scripts/vendor/generate_once.py）。

## 阶段与门禁

| 阶段 | 命令 | 门禁/纪律 |
|---|---|---|
| 初始化 | init --template T01..T03 --scene bedroom/cafe/street --authorize "<用户授权原文>" | 授权文本必须留痕；run 目录唯一；generate_once.py sha 必须=631936… 否则拒绝 |
| 关键帧生成 | image | 1 次 wan2.7-image-pro POST；失败不重提 |
| 目检门禁 | （人工/agent read_image） | 验收七项（手机直出感/动作中/背景使用痕迹/普通窗光/偏心或裁切/匀净微光泽肌/保留一个不完美）+ 鞋入画 + 无相机器材穿帮 + 饰品≤2 + 商品保真；≥6/7 才放行 |
| 放行 | approve --review-note "<目检结论>" | 目检记录写入 release（sha/时间/结论），未 approve 禁止 video |
| 视频生成 | video → poll → download | 1 次 happyhorse-1.1-i2v POST；poll 遇一过性 SSL EOF 允许续跑一次（无新 POST）；失败不重提 |
| 质检 | qa | ffprobe 规格（15s/≥360帧/1080×1920）+ 抽帧 f2/f6/f10/f14 目检八项（三拍/裙摆因果链/手指/脚底/脸漂移/裙褶闪烁/背景扭曲/结尾定格） |
| 投递 | deliver --dingtalk --web --mac | 钉钉幂等键=pipeline-<run>；web=frontend/assets/run-<日期>/（需另行 commit+push）；mac 先 /mnt/mac 超时兜底 scp |

## 提示词装配规则（init 自动执行）
- 首帧 prompt 取 docs/prompt-templates-v5.json keyframe_prompts[scene]（bedroom/street 已定版 v7；cafe 未定版会拒绝）。
- 视频 prompt 取 tiers[模板].video_prompt_en，并把其他场景的一致性句替换为目标场景句（背景只在首帧写定，i2v 仅一致性复述——背景错乱根因防线）。
- 人物/场景/稳定性规范见 docs/video-motion-prompt-spec.md v2.1 §9/§10；禁写词表见 prompt-templates-v5.json character_banned_words。

## 运维纪律（血泪条款）
1. 常驻进程（静态服务/隧道）必须 systemd 或 cron 上下文拉起；agent 工具上下文起的会被 cgroup 收尾杀掉。
2. 签名 URL（OSS artifact）永不进工具参数/提交物；状态组装一律磁盘内 python 完成。
3. /mnt/mac stale 时（命令 hang/D 状态）立即改 scp $MAC_SSH_TARGET，不重试挂载操作。
4. dws 发送必须 --yes（非交互）+ 幂等键；发后查 send-status 回执（deliver 已实现）；收件人=用户本人单聊（环境变量 DINGTALK_SELF_USER 注入，仓库不留个人 ID），无群发能力；Mac 兜底投递用环境变量 MAC_SSH_TARGET。
5. 每次生成单独用户授权；release.user_authorization 原文留痕；max_generation_posts=2 硬上限。
6. dsh-ui 围栏发出前必须 validate_dsh_ui（table 必须 rows 键）。

## 公网入口（ECS token 门控，A2-F3 补记载）
- 产品页公网 URL = https://<ECS-PUB-HOST>:3083/<token>/（TLS 复用 ECS relay 证书；token=32位随机hex，存 ECS /root/pitch-pub-token，不入仓库；错 token 404）。
- 链路：ECS pitch-pub.service(:3083) → loopback 13082 → VM 反向隧道(cron 保活) → pitch-httpd.service(:8811, systemd)。
- 轮换 token = ECS 云助手重生成 + 更新记忆条目；本管线 deliver 不经 ECS（仅 dingtalk/web/mac 三通道）。

## 已知局限
- 商品维度当前固定单商品（vendor generate_once.py 的 PRODUCT_FILE 硬编码 product_8822221153828）；多商品通用化需改 vendor 脚本，超出本版本范围。
- --template 接受 T01/T02/T03 别名或完整 tier id；--run 名限 [A-Za-z0-9_.-]（防注入）。
- 每阶段运行前复核 run 目录执行器 sha（防 init 后副本漂移）。

## 失败剧本
| 症状 | 处置 |
|---|---|
| download/poll SSL 握手超时或 EOF | 先分段诊断（curl -w / ip -6 route），确认链路在则续跑一次；不盲重试 |
| 关键帧目检不过 | 不重提 image（额度纪律）→ 回报用户决策；除非用户另行授权 |
| 视频 QA 规格不符 | 不重提 → 回报；降级建议 T03 |
| 钉钉发送 confirmation_required | 补 --yes（用户指令即授权） |
| GitHub 推送 | http.https://github.com/.proxy=socks5h://127.0.0.1:1090 已持久化 |

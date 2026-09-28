# 商品视频分镜提示词包（粉色百褶半身裙 · 人工生成用）

> 用途：配额恢复后由人工在千问平台生成视频，再把 mp4 交回集成。
> 模型建议：首选 wan2.7-i2v-2026-04-25（首帧=主图，保真最强）；兜底 happyhorse-1.1-t2v。
> 合规红线：画面不出现任何文字/水印/logo/促销贴纸；不出现无关服装配件；背景干净。

## 方案A：单条15秒（最省事）

**i2v 首帧**：main_image.png
**提示词（英文，直接粘贴）**：
E-commerce product video of a light pink pleated maxi skirt, 15 seconds. The skirt is the only garment featured: high waist, fine accordion pleats, A-line full swing, ankle length, soft polyester drape. Opening close-up of the pleats swaying, then slow pull-back to full silhouette on a clean off-white studio background, model walks slowly showing the swing and drape, gentle side light, final frame static full view centered. Smooth slow camera movement, professional studio lighting, photorealistic fabric texture, no text, no watermark, no logo, no other garments.

## 方案B：五段分镜（30秒，专家侧最佳形态）

每段单独生成（i2v 首帧用对应图），后期按序拼接：
1. **Hook 0-3s**（首帧=detail_3 工艺特写）：Extreme close-up of fine accordion pleats of a light pink maxi skirt, fabric gently swaying, soft studio light, shallow depth of field, no text.
2. **Problem 3-8s**（首帧=detail_4）：Medium shot, model holding the skirt at waist height against a clean background, showing the high waistband and stretch-free structure, slow tilt down, no text.
3. **Product 8-20s**（首帧=main_image）：Full-body model wearing the light pink pleated maxi skirt, slow walk and half turn showing the A-line swing and ankle length, clean off-white studio, even lighting, no text.
4. **Proof 20-25s**（首帧=detail_2）：Close-up of waistband and pleat stitching detail, fingers lightly brushing the fabric to show drape, macro lens, no text.
5. **CTA 25-30s**（首帧=detail_5 平铺）：Top-down flat lay of the skirt slowly zooming out, pleats fanned out symmetrically, soft shadow, final static centered frame, no text.

## 字幕脚本（SRT，外部烧录用，EN）

```
1
00:00:00,000 --> 00:00:03,000
Fine accordion pleats, made to move.

2
00:00:03,000 --> 00:00:08,000
High waist. No stretch. Clean structure.

3
00:00:08,000 --> 00:00:14,000
A-line swing, ankle length, effortless drape.

4
00:00:14,000 --> 00:00:20,000
Soft polyester, commute to casual.

5
00:00:20,000 --> 00:00:25,000
Every pleat, checked up close.

6
00:00:25,000 --> 00:00:30,000
Your everyday maxi skirt.
```

## BGM（fun-music-v1 生成）

提示词：Elegant upbeat instrumental, 100 BPM, light piano and soft strings, no vocals, 30 seconds, warm and confident mood.
混音备注：BGM 音量不超过人声/字幕感知的 30%；无配音时 BGM 均值 -20dB 左右。

## 市场禁忌备忘

- 韩国：避免画面/字幕出现数字 4 的强调排列；
- 巴西：避免大面积紫色作为主视觉（丧葬联想），本片粉色主调安全；
- 全市场：不出现品牌 logo、价格标签、促销贴纸。

## 验收标准（交回前自检）

- mp4/H.264 可播放，1080p，15-30 秒，<200MB；
- 抽 5 帧目检：商品颜色/版型与主图一致、无文字水印、背景干净；
- 首尾帧商品居中占比≥70%。

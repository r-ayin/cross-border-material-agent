#!/bin/bash
# Rebuild final 30s film: seg3 pillarbox fix (bg-color drawbox in t window) + concat + trim,
# then burn SRT subs and remux the already-mixed BGM audio from existing subbed file.
set -e
cd "${OUT_DIR:-$(dirname "$0")}"
SEG3F="drawbox=x=0:y=0:w=184:h=1440:color=0xE7E7E7:t=fill:enable=between(t\\,1.5\\,7.9),drawbox=x=1256:y=0:w=184:h=1440:color=0xE7E7E7:t=fill:enable=between(t\\,1.5\\,7.9),scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24"
NORM="scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24"
ffmpeg -y -v warning -i seg1_hook.mp4 -i seg2_problem.mp4 -i seg3_product.mp4 -i seg4_proof.mp4 -i seg5_cta.mp4 -filter_complex "[0:v]${NORM}[v0];[1:v]${NORM}[v1];[2:v]${SEG3F}[v2];[3:v]${NORM}[v3];[4:v]${NORM}[v4];[v0][v1][v2][v3][v4]concat=n=5:v=1:a=0[out]" -map "[out]" -c:v libx264 -crf 18 -preset medium -movflags +faststart full30.mp4
ffmpeg -y -v warning -i full30.mp4 -t 30 -c copy product_video_30s.mp4
ffmpeg -y -v warning -i product_video_30s.mp4 -i product_video_30s_subbed.mp4 -filter_complex "[0:v]subtitles=product_video_30s.srt:force_style='FontName=Nimbus Sans,Fontsize=10,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H00000000,Outline=2,Shadow=0,MarginV=28'[v]" -map "[v]" -map 1:a -c:v libx264 -crf 18 -preset medium -c:a copy -shortest -movflags +faststart subbed_new.mp4
mv subbed_new.mp4 product_video_30s_subbed.mp4
rm -f full30.mp4
ffprobe -v error -show_entries stream=codec_type,codec_name,width,height -of csv=p=0 product_video_30s_subbed.mp4
ffmpeg -v error -i product_video_30s_subbed.mp4 -vf "select='eq(n\\,300)+eq(n\\,660)'" -vsync vfr -s 512x512 fin_%d.png -y
ls -la product_video_30s.mp4 product_video_30s_subbed.mp4 fin_*.png

#!/bin/bash
# Extracts graded 30 fps frames (sharp + small blurred copy) from build/mc/raw.mp4
set -e
cd "$(dirname "$0")/../build/mc"
ffmpeg -v error -y -i raw.mp4 -vf "fps=30,scale=1080:1920:flags=lanczos,eq=contrast=1.06:saturation=1.04:gamma=0.98,colorbalance=bs=0.035:bm=0.01:rh=0.01,unsharp=5:5:0.4" -q:v 2 frames/%04d.jpg
ffmpeg -v error -y -i raw.mp4 -vf "fps=30,scale=270:480,gblur=sigma=9,eq=brightness=-0.12:saturation=0.8" -q:v 3 blur/%04d.jpg
ls frames | wc -l

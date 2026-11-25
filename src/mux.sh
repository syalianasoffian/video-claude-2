#!/usr/bin/env bash
# Mix voice + music + sfx and mux with rendered video.
# Usage: src/mux.sh <workdir with voice.wav music.wav sfx.wav video_noaudio.mp4> <out.mp4>
set -euo pipefail
D="$1"; OUT="$2"
ffmpeg -v error -y -i "$D/voice.wav" -i "$D/music.wav" -i "$D/sfx.wav" -filter_complex "
[0:a]atrim=0:21.4,highpass=f=80,equalizer=f=3000:t=q:w=1:g=2,acompressor=threshold=-20dB:ratio=3:attack=10:release=150:makeup=3dB,afade=t=out:st=21.05:d=0.3,apad=whole_dur=22.45,asplit=2[v][sc];
[1:a]volume='if(lt(t,21.0),0.16,0.16+0.30*min(1,(t-21.0)/0.5))':eval=frame[m];
[m][sc]sidechaincompress=threshold=0.03:ratio=4:attack=30:release=350[md];
[2:a]volume=0.55[s];
[v][md][s]amix=inputs=3:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[out]" \
  -map "[out]" -c:a pcm_s16le "$D/mix.wav"
ffmpeg -v error -y -i "$D/video_noaudio.mp4" -i "$D/mix.wav" -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k \
  -movflags +faststart -shortest "$OUT"

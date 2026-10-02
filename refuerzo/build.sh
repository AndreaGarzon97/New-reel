#!/usr/bin/env bash
# Arma el reel completo: marcas de sonido -> banda sonora -> cuadros -> mp4 final.
# Requisitos: node + playwright (con Chromium), python3 (numpy scipy pedalboard soundfile pyloudnorm), ffmpeg.
set -euo pipefail
cd "$(dirname "$0")"
export NODE_PATH="${NODE_PATH:-$(npm root -g)}"
OUT=../out/refuerzo_intermitente
TMP="${TMPDIR:-/tmp}/reel_refuerzo"
mkdir -p "$OUT" "$TMP"
[ -d node_modules/gsap ] || npm install

node render.cjs cues audio/cues.json                       # eventos sonoros, sincronizados con la animación
python3 audio/score.py                                       # -> audio/score.wav (-14 LUFS)
SEG_DIR="$TMP" node render.cjs video "$TMP/video_raw.mkv" "${JOBS:-4}"

# grano fílmico muy suave sólo en luminancia
VF="format=yuv444p,noise=c0s=5:c0f=t+u,format=yuv420p"
X264=(-c:v libx264 -preset slow -crf 17 -profile:v high -level 4.2 -r 30 -g 60 -bf 2 -movflags +faststart)

ffmpeg -hide_banner -loglevel error -y -i "$TMP/video_raw.mkv" -i audio/score.wav -map 0:v -map 1:a \
  -vf "$VF" "${X264[@]}" -c:a aac -b:a 256k -ar 48000 -shortest "$OUT/reel_refuerzo_intermitente.mp4"
ffmpeg -hide_banner -loglevel error -y -i "$TMP/video_raw.mkv" -an \
  -vf "$VF" "${X264[@]}" "$OUT/reel_refuerzo_intermitente_sin_musica.mp4"
ffmpeg -hide_banner -loglevel error -y -i audio/score.wav -c:a libmp3lame -b:a 256k "$OUT/musica_original.mp3"
node render.cjs cover "$OUT/portada.png"
echo "listo -> $OUT"

#!/usr/bin/env bash
# Regenera todo el reel: texturas → marcas de sonido → audio → cuadros → MP4 → portada.
set -euo pipefail
cd "$(dirname "$0")"
export FFMPEG="${FFMPEG:-$(command -v ffmpeg)}"
[ -d node_modules ] || npm install --no-audit --no-fund
python3 tools/make_textures.py
node tools/render.mjs --cues          # build/cues.json (sale de src/main.js)
python3 tools/audio.py                # build/audio.wav
node tools/render.mjs                 # dist/evitacion_reel.mp4 y dist/evitacion_reel_sin-audio.mp4
node tools/render.mjs --cover         # dist/portada.png
# copias para publicar
OUT=../out/evitacion
mkdir -p "$OUT"
cp dist/evitacion_reel.mp4 "$OUT/reel_evitacion.mp4"
cp dist/evitacion_reel_sin-audio.mp4 "$OUT/reel_evitacion_sin_musica.mp4"
cp dist/portada.png "$OUT/portada.png"
"$FFMPEG" -hide_banner -loglevel error -y -i build/audio.wav -c:a libmp3lame -b:a 192k "$OUT/musica_original.mp3"
echo "Listo → $OUT"

# Reel: comunicación asertiva (60 s)

Ilustración y animación generadas por código, con estética de dibujo a mano:
trazos que "tiemblan" (line boil), acuarela con bordes de pigmento, textura de
papel y crayón, letra manuscrita y animación "en dos" (15 dibujos por segundo).

## Archivos

- `out/reel_comunicacion_asertiva.mp4` — versión final 1080×1920, 30 fps, con música original (~26 MB).
- `out/reel_sin_musica.mp4` — misma animación sin audio (para sumarle un tema desde Instagram).
- Las versiones de mayor calidad (~48 MB) se generan con `render.py` y no se suben al repo.
- `out/portada.png` — portada sugerida.
- `reel/` — código fuente (`draw.py` trazos y texturas, `chars.py` personajes,
  `scenes.py` guion y tiempos, `music.py` música, `render.py` render final).

## Guion

| Tiempo | Escena | Texto en pantalla |
|---|---|---|
| 0–6 s | Gancho | Hay 3 formas de decir lo que te molesta… y solo una cuida a los dos. |
| 6–18 s | 1. Pasiva | Me callo para no pelear. · "No, nada… seguí vos." · Pero lo que no digo… se acumula. |
| 18–30 s | 2. Agresiva | Lo digo… pero atacando. · "¡Nunca me dejás hablar!" · Me escucha… pero se aleja. |
| 30–42 s | 3. Asertiva | Digo lo que siento y lo que necesito, con respeto. · "¿Me dejás terminar la idea?" · Me cuido a mí… y cuido el vínculo. |
| 42–54 s | Fórmula | 1. Lo que pasó: "Cuando me interrumpís," 2. Lo que sentís: "me frustra." 3. Lo que necesitás: "¿Me dejás terminar la idea?" · Tip: evitá el "siempre" y el "nunca". |
| 54–60 s | Cierre | Se trata de decir lo que sentís sin lastimar… y sin lastimarte. · guardalo para cuando lo necesites |

## Regenerar

```bash
pip install numpy pillow scipy skia-python   # y ffmpeg en el sistema
cd reel
python3 music.py                              # -> music.wav
python3 render.py --out ../out/reel_sin_musica.mp4
python3 cover.py ../out/portada.png
```

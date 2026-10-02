# Reel: refuerzo intermitente en los vínculos (60 s)

Reel tipográfico de estilo editorial (revista/cuaderno de laboratorio), animado por código
con una línea de tiempo determinista: cada cuadro se dibuja en Chromium y la música original
se sintetiza a partir de las mismas marcas de tiempo, así que el sonido cae justo en el cuadro.

**Paleta:** tinta `#15110F` · hueso `#EBE4D7` · borravino `#561320` · rojo señal `#D93A2B`
(`#B92D20` para texto chico sobre hueso) · grafito `#6E655C`.
**Tipografías (OFL):** Instrument Serif, Instrument Sans, IBM Plex Mono.

## Archivos

- `out/refuerzo_intermitente/reel_refuerzo_intermitente.mp4` — final 1080×1920, 30 fps, con música original.
- `out/refuerzo_intermitente/reel_refuerzo_intermitente_sin_musica.mp4` — sin audio (para sumar un tema desde Instagram).
- `out/refuerzo_intermitente/musica_original.mp3` — la banda sonora sola.
- `out/refuerzo_intermitente/portada.png` — portada (sirve recortada en la grilla 3:4).
- `out/refuerzo_intermitente/texto_para_publicar.md` — descripción, fuentes y texto alternativo.
- `refuerzo/` — código fuente: `index.html` + `css/reel.css` (diseño), `js/reel.js` (animación y
  marcas de sonido), `audio/score.py` (música y efectos), `render.cjs` (cuadros con Playwright),
  `cover.html` (portada) y `build.sh` (arma todo).

## Guion

| Tiempo | Escena | En pantalla |
|---|---|---|
| 0–4 s | Gancho | Globo de "escribiendo…" que aparece y desaparece. ¿Por qué engancha más quien te quiere *a veces*? |
| 4–10,4 s | Qué es | Entrada de diccionario: *refuerzo intermitente*. 1. Recompensa que llega solo a veces. 2. fig. Revisar el celular una y otra vez. |
| 10,4–18,4 s | Laboratorio | Fig. 1, registro acumulativo de picoteos (Ferster & Skinner, 1957): zona CON PREMIO y, tras una pausa en el corte, zona SIN PREMIO. Premio siempre: deja de picotear. Premio a veces (al azar): sigue picoteando ("todo esto, sin premio"), y se oyen los picoteos. Lo que llega *a veces* cuesta más soltarlo. |
| 18,4–24,4 s | Cerebro | Tragamonedas: corazón, corazón, cruz (casi). La dopamina responde más a lo *incierto* que a lo seguro (Fiorillo, Tobler & Schultz, 2003). |
| 24,4–33,6 s | Vínculos sanos | También hay intermitencia. Lo que varía: deseo, tiempo, sorpresas. La base: respeto, cuidado, seguridad. Varían los extras. *La base no se mueve.* |
| 33,6–40 s | Vínculos con violencia | Cuando hay violencia, lo que va y viene *es la base*. La violencia no es solo física. La línea estable se rompe en cariño / frialdad, atención / silencio, promesas / desprecio. |
| 40–47,2 s | Violencia | Ciclo de la violencia (Walker, 1979): tensión → explosión → luna de miel (el premio), y se repite. Y el *alivio* se confunde con amor (Dutton & Painter, 1981). |
| 47,2–54,4 s | La diferencia | Vínculo sano: lo impredecible es *la sorpresa*. Vínculo con violencia: lo impredecible es *cómo te van a tratar*. |
| 54,4–60 s | Cierre | Que te enganche no significa que *te haga bien*. Si vivís violencia en tu vínculo, no es tu culpa. Línea 144. Fuentes. |

## Regenerar

```bash
cd refuerzo
npm install                                     # gsap
pip install numpy scipy pedalboard soundfile pyloudnorm
./build.sh                                      # necesita node + playwright (Chromium) y ffmpeg
```

---

# Reel: comunicación asertiva (60 s)

Ilustración y animación generadas por código, con estética de dibujo a mano:
trazos que "tiemblan" (line boil), acuarela con bordes de pigmento, textura de
papel y crayón, letra manuscrita y animación "en dos" (15 dibujos por segundo).

## Archivos

- `out/reel_comunicacion_asertiva.mp4` — versión final 1080×1920, 30 fps, con música original (~26 MB).
- `out/reel_sin_musica.mp4` — misma animación sin audio (para sumarle un tema desde Instagram).
- Las versiones de mayor calidad (~48 MB) se generan con `render.py` y no se suben al repo.
- `out/portada.png` — portada sugerida.
- `out/personitas/reel_personitas_ukelele.mp4` — versión aparte con las personitas (buzo azul y pelirroja),
  música de ukelele y silbido, y `portada_personitas.png`. Se genera con
  `REEL_CHARS=people python3 render.py` y la música de `songs.py`.
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

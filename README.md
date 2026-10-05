# Reel: evitación y refuerzo negativo (60 s)

Por qué evitar alivia hoy y empeora mañana. Reel tipográfico animado por código: cada cuadro se
dibuja en Chromium con una línea de tiempo determinista y la música original se sintetiza a partir
de las mismas marcas de tiempo, así cada sonido cae justo en su cuadro.

**Idea visual:** una sola línea de "malestar" recorre el reel. Sube, se corta de golpe en lima cuando
evitás (el alivio) y la próxima vez sube antes y más alto, hasta salirse de escala. Al final, con
exposición gradual, cada pico es más bajo.

**Paleta** (sin durazno ni teal): noche `#0F111B` · cobalto `#2A3EA5` · resaltador lima `#DCE24B`
(el color del alivio: se siente bien, pero también es el color de "atención") · hueso `#ECE7DC`.
**Tipografías (OFL):** Archivo (condensada), Newsreader (itálica), Martian Mono y Reenie Beanie (notas a mano).

## Archivos

- `out/evitacion/reel_evitacion.mp4`: versión final, 1080×1920, 30 fps, con música original.
- `out/evitacion/reel_evitacion_sin_musica.mp4`: sin audio, para sumar un tema desde la app.
- `out/evitacion/musica_original.mp3`: la banda sonora sola.
- `out/evitacion/portada.png`: portada (entra recortada en la grilla 3:4).
- `out/evitacion/texto_para_publicar.md`: descripción para TikTok e Instagram, fuentes, texto alternativo y guion para voz.
- `evitacion/`: código fuente. `src/index.html` + `src/style.css` (diseño), `src/main.js` (animación, curva
  y marcas de sonido), `src/portada.html`, `tools/audio.py` (música y efectos), `tools/render.mjs`
  (cuadros con Playwright y MP4), `tools/make_textures.py` (papel y grano) y `build.sh` (arma todo).

## Guion

| Tiempo | Escena | En pantalla |
|---|---|---|
| 0–5 s | Gancho | Cancelaste ~~el plan~~. y sentiste *alivio*. (medidor de malestar: 8 → 2) · Ese alivio te está *entrenando*. |
| 5–12 s | Qué es | Se llama refuerzo *negativo* (nota: *no es un castigo*). Refuerzo: la conducta se repite. Negativo: porque te *saca* algo: *el malestar*. |
| 12–20 s | Hoy | La curva sube ("se acerca el plan"), EVITÁS, cae en lima: *alivio*. Hoy, evitar baja el malestar *al toque*. Y tu cerebro anota: "esto sirve". |
| 20–27 s | Lo que no ves | Línea punteada: si te quedabas, la ansiedad sube, toca techo… *y baja sola*. Pero tu cerebro anota: "zafé porque me fui". |
| 27–35 s | Mañana | La alarma suena *antes y más fuerte*: picos más altos, el último *fuera de escala*. |
| 35–41 s | El efecto | Y cada vez evitás *más*. Anillos: el plan, la reunión, el colectivo, llamar, salir; se tachan y el círculo se achica hasta "vos". Tu mundo *se achica*. |
| 41–47 s | La cuenta | Evitar es pagar con *tarjeta*. Ticket: hoy, alivio $ 0 · mañana, ansiedad · intereses, miedo · total: más miedo. Hoy no duele. El resumen llega *con intereses*. |
| 47–55 s | ¿Y entonces? | Andá con miedo, *de a poco*. Quedate un ratito más de lo que te pide el miedo. Cuatro exposiciones: *cada vez sube menos*. |
| 55–60 s | Cierre | Evitar te alivia *hoy* y te achica *mañana* ("achica" se achica). Guardalo para la próxima vez que quieras cancelar. — @lic.andreagarzon |

El final empalma con el principio ("…que quieras cancelar." → "Cancelaste el plan."), así el loop no corta.

## Regenerar

```bash
cd evitacion
pip install numpy scipy pillow
./build.sh            # necesita node + playwright (Chromium) y ffmpeg
node tools/render.mjs --preview 0.6,16.6,38   # cuadros sueltos en build/preview/ para revisar
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

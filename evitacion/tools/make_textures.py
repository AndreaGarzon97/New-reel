"""Texturas del reel: papel (manchas + fibra) y 6 cuadros de grano de película.

Todo centrado en gris medio, para usarse con mezcla soft-light / overlay sin
cambiar el color de cada escena.
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

OUT = Path(__file__).resolve().parent.parent / "src" / "tex"
OUT.mkdir(parents=True, exist_ok=True)
W, H = 1080, 1920
rng = np.random.default_rng(2611)


def noise(scale, blur):
    """ruido normalizado (media 0, desvío 1) con tamaño de mancha `scale`."""
    a = rng.normal(0, 1, (H // scale, W // scale)).astype(np.float32)
    im = Image.fromarray(((a - a.min()) / (np.ptp(a) + 1e-6) * 255).astype(np.uint8), "L")
    im = im.resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(blur))
    x = np.asarray(im, np.float32)
    return (x - x.mean()) / (x.std() + 1e-6)


def fibers():
    """fibras cortas en diagonal, como papel de diario."""
    a = rng.normal(0, 1, (H, W)).astype(np.float32)
    im = Image.fromarray(((a - a.min()) / np.ptp(a) * 255).astype(np.uint8), "L")
    im = im.rotate(28, resample=Image.BICUBIC).filter(ImageFilter.BoxBlur(0))
    # estirar en una dirección: desenfoque horizontal fuerte sobre la imagen rotada
    k = ImageFilter.Kernel((5, 5), [0, 0, 0, 0, 0,
                                    0, 0, 0, 0, 0,
                                    1, 1, 1, 1, 1,
                                    0, 0, 0, 0, 0,
                                    0, 0, 0, 0, 0], scale=5)
    for _ in range(3):
        im = im.filter(k)
    im = im.rotate(-28, resample=Image.BICUBIC)
    x = np.asarray(im, np.float32)
    return (x - x.mean()) / (x.std() + 1e-6)


paper = 0.6 * noise(60, 22) + 0.35 * noise(14, 4) + 0.22 * noise(1, 0.5) + 0.18 * fibers()
paper /= paper.std()
Image.fromarray((128 + paper * 13).clip(0, 255).astype(np.uint8), "L").save(OUT / "paper.png", optimize=True)

# grano a media resolución: el navegador lo escala y queda un grano de ~2 px
for i in range(6):
    g = rng.normal(128, 40, (H // 2, W // 2)).clip(0, 255).astype(np.uint8)
    Image.fromarray(g, "L").filter(ImageFilter.GaussianBlur(0.5)).save(OUT / f"grain{i}.png", optimize=True)

print("ok", sorted(p.name for p in OUT.iterdir()))

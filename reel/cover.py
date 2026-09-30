"""Cover image for the reel (safe inside the 3:4 grid crop)."""
import sys

import numpy as np
import skia
from PIL import Image

from chars import cloud, heart, draw_char
from draw import Ctx, H, W, font, lettering, film_grain
from scenes import BRUSH, HAND, SAGE_D, TERRA, TAG, charA, charB, draw_bg, ground_line, underline, text_width

surf = skia.Surface(W, H)
cv = surf.getCanvas()
ctx = Ctx(cv, 3, 10.0)
draw_bg(ctx, 'asertiva')
ground_line(ctx, 'asertiva')

f1 = font(BRUSH, 150)
lettering(ctx, 'Comunicación', W / 2, 440, f1, 'cv1', weight=1.0)
f2 = font(BRUSH, 190)
x0, tot = lettering(ctx, 'asertiva', W / 2, 625, f2, 'cv2', color=SAGE_D, weight=1.2)
underline(ctx, x0 + 10, x0 + tot - 10, 665, 'cvul', color=SAGE_D, width=8)
lettering(ctx, 'decir lo que sentís sin lastimar', W / 2, 775, font(HAND, 66), 'cv3', weight=1.4)
lettering(ctx, '(y sin lastimarte)', W / 2, 860, font(HAND, 66), 'cv4', weight=1.4, color=TERRA)

A = charA(x=322, eyes='happy', mouth=0.9, look=(4, 0), arms=('rest', ('abs', 478, 1300, 0.1)))
B = charB(x=658, eyes='happy', mouth=0.9, look=(-4, 0), arms=(('abs', 502, 1300, -0.1), 'rest'))
draw_char(ctx, A, 'A')
draw_char(ctx, B, 'B')
heart(ctx, 490, 1040, 34, 'heart')

p = skia.Paint()
p.setBlendMode(skia.BlendMode.kOverlay)
p.setAlphaf(0.45)
cv.drawImage(film_grain(0), 0, 0, skia.SamplingOptions(), p)
out = sys.argv[1] if len(sys.argv) > 1 else 'cover.png'
Image.fromarray(surf.makeImageSnapshot().toarray()[..., [2, 1, 0]]).save(out)

"""Previews for the improved people in three palettes: character sheet, reel frame and
pasiva / agresiva / asertiva panels.   python3 people_opts.py"""
import os

import numpy as np
import skia
from PIL import Image

import alt_chars as ac
from chars import bubble, cloud as worry, heart
from draw import H, W, Ctx, film_grain, font
from options import hero_text
from people import VERSIONS, person2
from scenes import HAND, draw_bg, ground_line, signature

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out', 'personas')
CROP = (560, 1640)


def frame(bg, ground=True):
    surf = skia.Surface(W, H)
    ctx = Ctx(surf.getCanvas(), 2, 0.4)
    draw_bg(ctx, bg)
    if ground:
        ground_line(ctx, bg)
    return surf, ctx


def finish(surf, ctx):
    p = skia.Paint()
    p.setBlendMode(skia.BlendMode.kOverlay)
    p.setAlphaf(0.45)
    ctx.cv.drawImage(film_grain(0), 0, 0, skia.SamplingOptions(), p)
    return Image.fromarray(surf.makeImageSnapshot().toarray()[..., [2, 1, 0]])


def scene(ctx, V, state):
    boy, girl = V['boy'], V['girl']
    if state == 'pasiva':
        worry(ctx, 330, 860, 44, 'wc', dark=0.3, swirls=1, rain=0.8, t=0.4)
        person2(ctx, 330, 1400, 0.98, boy, 'sad', 'A', arms=('crossed', 'crossed'), shrink=1)
        person2(ctx, 735, 1400, 1.0, girl, 'talk', 'B', arms=('open', 'rest'), look=(-3, 0))
        bubble(ctx, 775, 770, 290, 130, (745, 895), 'bla', lines=['bla bla bla...'], fnt=font(HAND, 58))
    elif state == 'agresiva':
        person2(ctx, 345, 1400, 1.05, boy, 'angry', 'A', arms=('clench', 'point'), lean=0.04)
        person2(ctx, 805, 1400, 0.95, girl, 'scared', 'B', arms=('guard', 'guard'), lean=-0.08, step=1)
        ac.anger_marks(ctx, np.array([280.0, 900.0]), 1.0, 'amA')
        ac.sweat(ctx, np.array([895.0, 965.0]), 1.0, 'swB')
    else:
        mid = (540, 1262)
        person2(ctx, 400, 1400, 1.0, boy, 'smile', 'A', arms=('rest', 'rest'), hands_to=(None, (528, 1250)), look=(3, 0))
        person2(ctx, 680, 1400, 1.0, girl, 'happy', 'B', arms=('rest', 'rest'), hands_to=((552, 1250), None))
        heart(ctx, 540, 990, 30, 'hrt')


def render(vk):
    os.makedirs(OUT, exist_ok=True)
    V = VERSIONS[vk]
    # character sheet
    surf, ctx = frame('hook', ground=False)
    person2(ctx, 320, 1480, 1.4, V['boy'], 'smile', 'A', arms=('rest', 'wave'), look=(2, 0))
    person2(ctx, 760, 1480, 1.4, V['girl'], 'happy', 'B', arms=('rest', 'rest'))
    finish(surf, ctx).crop((0, 740, W, 1540)).resize((900, 667), Image.LANCZOS).save(
        os.path.join(OUT, f'{vk}_ficha.jpg'), quality=87)
    for state in ('pasiva', 'agresiva', 'asertiva'):
        surf, ctx = frame(state)
        scene(ctx, V, state)
        finish(surf, ctx).crop((0, CROP[0], W, CROP[1])).resize((600, 600), Image.LANCZOS).save(
            os.path.join(OUT, f'{vk}_{state}.jpg'), quality=86)
    surf, ctx = frame('asertiva')
    hero_text(ctx)
    scene(ctx, V, 'asertiva')
    signature(ctx)
    finish(surf, ctx).resize((720, 1280), Image.LANCZOS).save(os.path.join(OUT, f'{vk}_reel.jpg'), quality=86)


if __name__ == '__main__':
    for vk in VERSIONS:
        render(vk)
        print('ok', vk, flush=True)

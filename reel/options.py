"""Renders the character-option previews: for each family a full reel frame
(hero) plus pasiva / agresiva / asertiva panels.   python3 options.py [name ...]"""
import math
import os
import sys

import numpy as np
import skia
from PIL import Image

import alt_chars as ac
from chars import bubble, cloud as worry, heart
from draw import H, INK, W, Ctx, film_grain, font, rgb
from scenes import HAND, SAGE_D, draw_bg, ground_line, label, say_lines, signature

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out', 'personajes')
CROP = (560, 1640)
T = 0.4  # time used for rain / animation phases


def new_frame(bg):
    surf = skia.Surface(W, H)
    ctx = Ctx(surf.getCanvas(), 2, T)
    draw_bg(ctx, bg)
    ground_line(ctx, bg)
    return surf, ctx


def finish(surf, ctx):
    p = skia.Paint()
    p.setBlendMode(skia.BlendMode.kOverlay)
    p.setAlphaf(0.45)
    ctx.cv.drawImage(film_grain(0), 0, 0, skia.SamplingOptions(), p)
    return Image.fromarray(surf.makeImageSnapshot().toarray()[..., [2, 1, 0]])


def bla(ctx, x, y, tail):
    bubble(ctx, x, y, 290, 130, tail, 'bla', lines=['bla bla bla...'], fnt=font(HAND, 58))


def hero_text(ctx):
    label(ctx, 20, 0, 3, 'Asertiva', SAGE_D, 'lab3')
    say_lines(ctx, 20, 0, ['Digo lo que siento', 'y lo que necesito,', [('con respeto.', SAGE_D)]], 395, 104, 'as1')
    say_lines(ctx, 20, 0, ['Me cuido a mí...', [('y cuido el vínculo.', SAGE_D)]], 745, 106, 'as2')


def swirl_bg(ctx, c=(540, 1150), max_r=900):
    for j, r in enumerate(range(90, max_r, 85)):
        a0 = (j * 1.3) % 6.28
        for k in range(3):
            th = np.linspace(a0 + k * 2.1, a0 + k * 2.1 + 1.5, 40)
            ctx.line(np.stack([c[0] + r * np.cos(th), c[1] + r * 0.9 * np.sin(th)], 1), 4.5,
                     color=rgb('#FFFDF6'), alpha=0.75, key=('swirl', j, k), taper=(0.2, 0.2), amp=1.5)


# --------------------------------------------------------------------------

def globos(ctx, state):
    if state == 'pasiva':
        worry(ctx, 330, 1000, 42, 'wc', dark=0.3, swirls=1, rain=0.8, t=T)
        ac.balloon(ctx, 330, 1200, 78, ac.BAL_A, 'sad', 'A', (330, 1400), accessory='tuft', squash=0.86, wrinkle=1,
                   slack=0.7)
        ac.balloon(ctx, 720, 1040, 110, ac.BAL_B, 'talk', 'B', (705, 1400), accessory='glasses')
        bla(ctx, 760, 820, (730, 925))
    elif state == 'agresiva':
        ac.tension(ctx, np.array([350.0, 1030.0]), 176, 'tA', color=rgb('#B8432F'))
        ac.balloon(ctx, 350, 1030, 150, ac.BAL_A, 'angry', 'A', (350, 1400), accessory='tuft', flush=0.72)
        ac.balloon(ctx, 820, 1010, 86, ac.BAL_B, 'scared', 'B', (690, 1400), accessory='glasses', tilt=0.25, slack=-0.4)
        ac.sweat(ctx, np.array([905.0, 930.0]), 1.0, 'swB')
    else:
        knot = np.array([540.0, 1360.0])
        ac.balloon(ctx, 385, 1060, 112, ac.BAL_A, 'happy', 'A', knot, accessory='tuft', tilt=-0.08)
        ac.balloon(ctx, 695, 1060, 112, ac.BAL_B, 'happy', 'B', knot, accessory='glasses', tilt=0.08)
        for sg in (-1, 1):  # little bow where the strings are tied
            loop = ac.ell(540 + sg * 16, 1352, 16, 9, 20)
            ctx.loop(loop, 3.2, key=('bow', sg), amp=0.4)
        heart(ctx, 540, 930, 30, 'hrt')


def corazones(ctx, state):
    if state == 'pasiva':
        worry(ctx, 330, 960, 44, 'wc', dark=0.3, swirls=1, rain=0.8, t=T)
        ac.heart_char(ctx, 330, 1400, 0.92, ac.HEART_A, 'sad', 'A', arms=('shy', 'shy'), lean=-0.05)
        ac.heart_char(ctx, 720, 1400, 1.02, ac.HEART_B, 'talk', 'B', arms=('open', 'rest'), look=(-3, 0))
        bla(ctx, 760, 850, (735, 1000))
    elif state == 'agresiva':
        ac.heart_char(ctx, 340, 1400, 1.18, ac.HEART_A, 'angry', 'A', arms=('up', 'point'), flame=1.0, lean=0.06)
        ac.heart_char(ctx, 800, 1400, 0.9, ac.HEART_B, 'scared', 'B', arms=('guard', 'guard'), lean=-0.12, crack=1.0,
                      step=1)
        ac.sweat(ctx, np.array([905.0, 1070.0]), 1.0, 'swB')
    else:
        mid = (540, 1330)
        ac.heart_char(ctx, 420, 1400, 1.0, ac.HEART_A, 'peace', 'A', sit=True, hands_to=(None, mid))
        ac.heart_char(ctx, 660, 1400, 1.0, ac.HEART_B, 'peace', 'B', sit=True, hands_to=(mid, None))
        heart(ctx, 540, 1000, 30, 'hrt')


def nubes(ctx, state):
    if state == 'pasiva':
        ac.cloud_char(ctx, 320, 1180, 0.78, ac.CLOUD_A, 'sad', 'A', dark=0.3, rain=1.0, arms=((1.2, 0.9), (1.2, 0.9)), t=T)
        ac.cloud_char(ctx, 740, 1060, 0.95, ac.CLOUD_B, 'talk', 'B', arms=((-0.6, 1.0), (0.4, 0.9)), look=(-3, 0),
                      swirls=2)
        bla(ctx, 760, 850, (740, 960))
    elif state == 'agresiva':
        ac.cloud_char(ctx, 360, 1050, 1.1, ac.CLOUD_A, 'angry', 'A', dark=0.7, bolt=1.0, arms=((-0.7, 1.0), (-0.1, 1.2)),
                      swirls=4)
        ac.cloud_char(ctx, 820, 1150, 0.7, ac.CLOUD_B, 'scared', 'B', arms=((-1.0, 0.9), (-1.0, 0.9)), swirls=2)
        ac.sweat(ctx, np.array([905.0, 1060.0]), 1.0, 'swB')
    else:
        cols = ['#E9A3A0', '#F2C58A', '#EDE08F', '#B5CF9A', '#9DBBDD']
        for j, cc in enumerate(cols):
            r = 330 - j * 26
            th = np.linspace(np.pi * 1.05, np.pi * 1.95, 60)
            arc = np.stack([540 + r * np.cos(th), 1260 + r * 0.95 * np.sin(th)], 1)
            ctx.line(arc, 24, color=rgb(cc), key=('rb', j), alpha=0.85, taper=(0.03, 0.03), amp=1.5)
        mid = (540, 1130)
        ac.cloud_char(ctx, 330, 1130, 0.85, ac.CLOUD_A, 'happy', 'A', hands_to=(None, mid))
        ac.cloud_char(ctx, 750, 1130, 0.85, ac.CLOUD_B, 'happy', 'B', hands_to=(mid, None), swirls=2)


def personitas(ctx, state):
    if state == 'pasiva':
        worry(ctx, 330, 880, 44, 'wc', dark=0.3, swirls=1, rain=0.8, t=T)
        ac.person(ctx, 330, 1400, 0.98, 'boy', 'sad', 'A', arms=('crossed', 'crossed'), shrink=1)
        ac.person(ctx, 730, 1400, 1.0, 'girl', 'talk', 'B', arms=('open', 'rest'), look=(-3, 0))
        bla(ctx, 770, 780, (745, 900))
    elif state == 'agresiva':
        ac.person(ctx, 350, 1400, 1.05, 'boy', 'angry', 'A', arms=('fist', 'point'), lean=0.04)
        ac.person(ctx, 800, 1400, 0.95, 'girl', 'scared', 'B', arms=('guard', 'guard'), lean=-0.08, step=1)
        ac.anger_marks(ctx, np.array([285.0, 930.0]), 1.0, 'amA')
        ac.sweat(ctx, np.array([880.0, 990.0]), 1.0, 'swB')
    else:
        mid = (540, 1270)
        ac.person(ctx, 400, 1400, 1.0, 'boy', 'happy', 'A', arms=('rest', 'rest'), hands_to=(None, mid))
        ac.person(ctx, 680, 1400, 1.0, 'girl', 'happy', 'B', arms=('rest', 'rest'), hands_to=(mid, None))
        heart(ctx, 540, 1000, 30, 'hrt')


def manos(ctx, state, hero=False):
    swirl_bg(ctx, c=(540, 1190) if hero else (540, 1150), max_r=360 if hero else 900)
    if state == 'pasiva':
        ac.hand_char(ctx, (270, 1290), 0.35, 1.15, ac.HAND_A, 'fist', 'A', arm_from=(-80, 1480))
        ac.hand_char(ctx, (780, 1100), -1.05, 1.0, ac.HAND_B, 'talk', 'B', arm_from=(1180, 1260), flip=True, talk_open=0.7)
        for j in range(3):
            a = -2.2 + j * 0.35
            p0 = np.array([600.0, 1020.0]) + np.array([math.cos(a), math.sin(a)]) * 20
            ctx.line([p0, p0 + np.array([math.cos(a), math.sin(a)]) * 34], 4.2, key=('tk', j))
        bla(ctx, 700, 850, (650, 980))
    elif state == 'agresiva':
        ac.hand_char(ctx, (300, 1120), 1.45, 1.1, ac.HAND_A, 'point', 'A', arm_from=(-80, 1340), flush=0.35)
        for j in range(3):
            y = 1080 + j * 26
            ctx.line([[140, y], [220, y]], 4.2, key=('mv', j), alpha=0.7)
        ac.hand_char(ctx, (840, 1010), -0.35, 0.9, ac.HAND_B, 'splay', 'B', arm_from=(1180, 1250), flip=True)
        for j in range(3):
            x = 700 - j * 20
            ctx.line([[x, 900 + j * 10], [x - 8, 930 + j * 10], [x, 960 + j * 10]], 3.6, key=('sh', j), alpha=0.7)
        ac.sweat(ctx, np.array([930.0, 880.0]), 1.0, 'swB')
    else:
        ac.hand_char(ctx, (385, 1150), 1.2, 1.0, ac.HAND_A, 'relaxed', 'A', arm_from=(-80, 1360))
        ac.hand_char(ctx, (695, 1150), -1.2, 1.0, ac.HAND_B, 'relaxed', 'B', arm_from=(1160, 1360), flip=True)
        heart(ctx, 540, 960, 30, 'hrt')
        for j, a in enumerate((-2.4, -1.57, -0.75)):
            d = np.array([math.cos(a), math.sin(a)])
            ctx.line([np.array([540.0, 960.0]) + d * 50, np.array([540.0, 960.0]) + d * 76], 4.0, key=('sp', j),
                     color=rgb('#D9604F'))


FAMILIES = {'globos': globos, 'corazones': corazones, 'nubes': nubes, 'personitas': personitas, 'manos': manos}


def render_family(name):
    os.makedirs(OUT, exist_ok=True)
    fn = FAMILIES[name]
    for state in ('pasiva', 'agresiva', 'asertiva'):
        surf, ctx = new_frame(state)
        fn(ctx, state)
        im = finish(surf, ctx).crop((0, CROP[0], W, CROP[1])).resize((600, 600), Image.LANCZOS)
        im.save(os.path.join(OUT, f'{name}_{state}.jpg'), quality=86)
    surf, ctx = new_frame('asertiva')
    hero_text(ctx)
    if name == 'manos':
        fn(ctx, 'asertiva', hero=True)
    else:
        fn(ctx, 'asertiva')
    signature(ctx)
    finish(surf, ctx).resize((720, 1280), Image.LANCZOS).save(os.path.join(OUT, f'{name}_reel.jpg'), quality=86)


def render_current():
    from render import render_time
    for state, t in (('pasiva', 16.5), ('agresiva', 21.5), ('asertiva', 40.5)):
        a = render_time(t)
        im = Image.fromarray(a[..., [2, 1, 0]]).crop((0, CROP[0], W, CROP[1])).resize((600, 600), Image.LANCZOS)
        im.save(os.path.join(OUT, f'actual_{state}.jpg'), quality=86)
    Image.fromarray(render_time(41.3)[..., [2, 1, 0]]).resize((720, 1280), Image.LANCZOS).save(
        os.path.join(OUT, 'actual_reel.jpg'), quality=86)


if __name__ == '__main__':
    names = sys.argv[1:] or list(FAMILIES) + ['actual']
    for nm in names:
        if nm == 'actual':
            render_current()
        else:
            render_family(nm)
        print('ok', nm, flush=True)

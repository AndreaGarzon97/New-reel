"""Storyboard: six scenes, timed to the music (80 bpm, one bar = 3 s)."""
import math
from functools import lru_cache

import numpy as np
import skia

from chars import (BLUE, CORAL, Char, bubble, cloud, draw_char, heart, scribble_circle, underline)
from draw import (INK, NTEX, Ctx, H, W, fbm, font, glyph_count, lettering, paper_rgb, rgb, rgb_image,
                  text_width)

HAND = 'CoveredByYourGrace.ttf'
BRUSH = 'CaveatBrush-Regular.ttf'
SLATE = rgb('#4A6789')
TERRA = rgb('#B24E3A')
SAGE_D = rgb('#4D7856')
TAG = rgb('#6F8A6E')
GROUND_Y = 1400

# scene boundaries (seconds); transitions are centred on them
BOUNDS = [0, 6, 18, 30, 42, 54, 60]


# --------------------------------------------------------------------------
# timing helpers
# --------------------------------------------------------------------------

def ease(u, kind='io'):
    u = min(1.0, max(0.0, u))
    if kind == 'io':
        return u * u * (3 - 2 * u)
    if kind == 'o':
        return 1 - (1 - u) ** 3
    if kind == 'i':
        return u ** 3
    if kind == 'back':
        c = 2.2
        return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2
    return u


def kf(t, keys, kind='io'):
    """keyframes [(time, value), ...] -> value at t (values may be tuples)."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            u = ease((t - t0) / (t1 - t0), kind)
            if isinstance(v0, tuple):
                return tuple(a + (b - a) * u for a, b in zip(v0, v1))
            return v0 + (v1 - v0) * u
    return keys[-1][1]


def pop(t, t_in, t_out=None, dur=0.28):
    """bubble scale: pops in with overshoot, shrinks out."""
    if t < t_in:
        return 0.0
    sc = ease((t - t_in) / dur, 'back')
    if t_out is not None and t > t_out:
        sc *= 1 - ease((t - t_out) / 0.2, 'i')
    return max(0.0, sc)


def walk(t, t0, t1, x0, x1, stride=70.0):
    x = kf(t, [(t0, x0), (t1, x1)], 'io')
    if t0 < t < t1:
        return x, abs(x - x0) / stride * math.pi
    return x, None


def talk(t, speed=13.0, lo=0.2, hi=0.6):
    return lo + (hi - lo) * (0.5 + 0.5 * math.sin(t * speed))


# --------------------------------------------------------------------------
# text helpers
# --------------------------------------------------------------------------

def fit_font(name, size, segs, max_w):
    f = font(name, size)
    w = text_width(segs, f)
    if w > max_w:
        f = font(name, size * max_w / w)
    return f


def say(ctx, t, t0, segs, y, key, size=96, name=HAND, cps=26.0, color=INK, weight=1.7, x=W / 2,
        align='center', max_w=900, alpha=1.0, **kw):
    if t < t0:
        return None
    if isinstance(segs, str):
        segs = [(segs, color)]
    f = fit_font(name, size, segs, max_w)
    x0, total = lettering(ctx, segs, x, y, f, key, reveal=(t - t0) * cps, align=align, weight=weight,
                          alpha=alpha, **kw)
    return x0, total, f


def say_lines(ctx, t, t0, lines, y0, dy, key, cps=26.0, **kw):
    """several lines written one after the other; returns time the last one ends."""
    tt = t0
    for i, ln in enumerate(lines):
        say(ctx, t, tt, ln, y0 + i * dy, (key, i), cps=cps, **kw)
        tt += glyph_count(ln) / cps + 0.12
    return tt


def seg_span(segs, idx, f):
    x = sum(text_width([s], f) for s in segs[:idx])
    return x, x + text_width([segs[idx]], f)


def label(ctx, t, t0, num, word, color, key, y=258):
    """'(1) Pasiva' style heading: number in a scribbled circle + brush word."""
    if t < t0:
        return
    f = font(BRUSH, 112)
    fw = text_width(word, f)
    total = fw + 110
    x0 = W / 2 - total / 2
    cx = x0 + 40
    scribble_circle(ctx, cx, y - 34, 42, 46, (key, 'circ'), upto=ease((t - t0) / 0.35), color=color, width=5.5)
    lettering(ctx, str(num), cx, y - 4, font(BRUSH, 78), (key, 'num'), reveal=(t - t0 - 0.1) * 20, color=color)
    lettering(ctx, word, x0 + 110, y, f, (key, 'w'), reveal=(t - t0 - 0.2) * 22, align='left',
              color=color, weight=1.0)


# --------------------------------------------------------------------------
# backgrounds (static washes, built once per process)
# --------------------------------------------------------------------------

def _tint(img, color, wmap, paper_norm):
    c = np.array([int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)], np.float32) / 255
    tinted = c[None, None, :] * paper_norm[..., None]
    return img * (1 - wmap[..., None]) + tinted * wmap[..., None]


@lru_cache(None)
def _base_fields():
    paper = paper_rgb()
    base = np.array([0xF1, 0xE8, 0xD6], np.float32) / 255
    pn = (paper / base[None, None, :]).mean(2)
    from draw import streaks, fine_grain
    cov = np.clip(0.72 + 0.35 * streaks(H, W, 71, 60, 3, angle=-12) + 0.2 * (fine_grain(H, W, 72, 0.8) - 0.5), 0, 1)
    blot = fbm(H, W, [(4, 1.0), (10, 0.5)], 73)
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None] * np.ones((1, W), np.float32)
    xx = np.linspace(0, 1, W, dtype=np.float32)[None, :] * np.ones((H, 1), np.float32)
    return paper, pn, cov, blot, yy, xx


def _sky(img, pn, cov, blot, yy, top, y_fade, strength=0.9, extra=None):
    w = np.clip(1 - yy / y_fade, 0, 1) ** 0.9 * strength * cov * (0.85 + 0.3 * blot)
    return _tint(img, top, np.clip(w, 0, 1), pn)


@lru_cache(None)
def background(name):
    paper, pn, cov, blot, yy, xx = _base_fields()
    img = paper.copy()
    if name == 'pasiva':
        img = _sky(img, pn, cov, blot, yy, '#B9C6D6', 0.62)
    elif name == 'agresiva':
        img = _sky(img, pn, cov, blot, yy, '#F0BBA0', 0.62)
    elif name == 'asertiva':
        img = _sky(img, pn, cov, blot, yy, '#F0D596', 0.66, strength=0.95)
    elif name == 'formula':
        d = ((xx - 0.5) / 0.55) ** 2 + ((yy - 0.47) / 0.42) ** 2
        w = np.clip(1 - d, 0, 1) ** 0.6 * 0.45 * cov * (0.8 + 0.4 * blot)
        img = _tint(img, '#F2DDA4', w, pn)
    elif name == 'cierre':
        # sunset: warm glow low in the sky, greyish-sage at the top
        img = _tint(img, '#A9B7A6', np.clip(1 - yy / 0.35, 0, 1) * 0.8 * cov, pn)
        d = ((xx - 0.45) / 0.8) ** 2 + ((yy - 0.52) / 0.32) ** 2
        img = _tint(img, '#F0CD86', np.clip(1.15 - d, 0, 1) ** 0.8 * 0.95 * cov * (0.85 + 0.3 * blot), pn)
    surf = skia.Surface(W, H)
    cv = surf.getCanvas()
    cv.drawImage(rgb_image(img), 0, 0)
    ctx = Ctx(cv, 0)
    xs = np.linspace(-40, W + 40, 80)
    if name in ('hook', 'pasiva', 'agresiva', 'asertiva'):
        if name == 'asertiva':
            hill = np.stack([xs, 1245 - 85 * np.exp(-((xs - 820) / 260) ** 2) - 40 * np.exp(-((xs - 200) / 200) ** 2)], 1)
            ctx.wash(np.vstack([hill, [[W + 40, 1500], [-40, 1500]]]), rgb('#C9D1A6'), key='hill2', amp=6, edge=0.4)
        gcol = {'hook': '#BFCAA4', 'pasiva': '#AEB9AE', 'agresiva': '#D2BE8E', 'asertiva': '#A9BD8C'}[name]
        gy = GROUND_Y + 6 * np.sin(xs / 150)
        ctx.wash(np.vstack([np.stack([xs, gy], 1), [[W + 40, H + 40], [-40, H + 40]]]), rgb(gcol), key=('g', name),
                 amp=5, edge=0.35)
    if name == 'cierre':
        mt = np.stack([xs, 1085 - 150 * np.exp(-((xs - 800) / 190) ** 2) - 70 * np.exp(-((xs - 1000) / 150) ** 2)], 1)
        ctx.wash(np.vstack([mt, [[W + 40, 1100], [-40, 1100]]]), rgb('#B6BC9C'), key='mt', amp=4, edge=0.4)
        sea = np.vstack([np.stack([xs, 1085 + 3 * np.sin(xs / 90)], 1), [[W + 40, 1400], [-40, 1400]]])
        ctx.wash(sea, rgb('#86A596'), key='sea', amp=5, edge=0.3)
        ctx.wash(np.vstack([np.stack([xs, _hill_y(xs)], 1), [[W + 40, H + 40], [-40, H + 40]]]),
                 rgb('#9EB08C'), key='hillc', amp=5, edge=0.45)
    return surf.makeImageSnapshot()


def _hill_y(xs):
    xs = np.asarray(xs, np.float64)
    return 1330 - 40 * np.exp(-((xs - 520) / 330) ** 2) + 0.00008 * (xs - 520) ** 2 * 1.2


def ground_line(ctx, name):
    xs = np.linspace(-20, W + 20, 60)
    ctx.line(np.stack([xs, GROUND_Y + 6 * np.sin(xs / 150)], 1), 5.0, key=('hz', name), taper=(0.02, 0.02), amp=1.5)
    r = np.random.default_rng(5)
    for j in range(9):
        gx = 60 + j * 118 + r.integers(-30, 30)
        gy = GROUND_Y + 30 + r.integers(0, 110)
        if 290 < gx < 790:  # keep the signature area clean
            continue
        for k in range(3):
            a = -math.pi / 2 + (k - 1) * 0.45
            ctx.line([[gx + k * 7, gy], [gx + k * 7 + 16 * math.cos(a), gy + 22 * math.sin(a)]], 3.6,
                     key=('tuft', name, j, k), alpha=0.7, taper=(0.05, 0.5))
    if name == 'asertiva':
        hx = np.linspace(-20, W + 20, 60)
        hy = 1245 - 85 * np.exp(-((hx - 820) / 260) ** 2) - 40 * np.exp(-((hx - 200) / 200) ** 2)
        ctx.line(np.stack([hx, hy], 1), 4.2, key='hill2l', alpha=0.8, taper=(0.02, 0.02))


HANDLE = '@lic.andreagarzon'
HANDLE_Y = 1470  # lowest spot that stays visible above Instagram's caption overlay


def signature(ctx):
    lettering(ctx, HANDLE, W / 2, HANDLE_Y, font('Caveat.ttf', 60), 'handle', color=rgb('#2E2724', 0.78),
              weight=0.6, rot=1.2, bounce=1.5)


def draw_bg(ctx, name):
    ctx.cv.drawImage(background(name), 0, 0)


# --------------------------------------------------------------------------
# characters' default looks
# --------------------------------------------------------------------------

GS = 1.12  # global character scale


def charA(**kw):
    d = dict(name='A', x=290, s=1.1, color=BLUE, hair='tuft')
    d.update(kw)
    d['s'] *= GS
    return Char(**d)


def charB(**kw):
    d = dict(name='B', x=690, s=1.1, color=CORAL, hair='sprout')
    d.update(kw)
    d['s'] *= GS
    return Char(**d)


def mouth_pt(c):
    """rough world position of a character's mouth (for bubble tails)."""
    return (c.x + c.look[0] * c.s, c.y + c.s * (-LEG_Y - (128 - 10) + 20) + 40)


LEG_Y = 84


# --------------------------------------------------------------------------
# scenes (t is local time; slightly negative / beyond the end during wipes)
# --------------------------------------------------------------------------

def s_hook(ctx, t):
    draw_bg(ctx, 'hook')
    ground_line(ctx, 'hook')
    # the other one talks and talks
    arms_b = ('open', 'rest') if math.sin(t * 5) > 0 else ('rest', 'open')
    B = charB(eyes='happy', mouth=0.6, mouth_open=talk(t), arms=arms_b, look=(-3, 0))
    # A tries to say something and gives up
    tries = 1.7 < t < 2.5
    A = charA(brow=kf(t, [(0.8, 0.0), (1.4, 0.45)]), mouth=-0.1, wavy=0.7, look=(4, 0),
              mouth_open=0.3 if tries else 0.0, arms=('rest', 'wave' if tries else 'rest'))
    cloud(ctx, 290, 880, 52 * pop(t, 0.9, dur=0.4), 'cloud', dark=0.15, swirls=1, t=t)
    draw_char(ctx, A, 'A')
    draw_char(ctx, B, 'B')
    bubble(ctx, 715, 845, 300, 140, (680, 985), 'bla', scale=pop(t, 0.25),
           lines=['bla bla bla...'], fnt=font(HAND, 64), reveal=((t - 0.4) * 13) % 22)

    say(ctx, t, -0.3, 'comunicación asertiva', 250, 'tag', size=48, name=BRUSH, color=TAG, weight=0, cps=60)
    say_lines(ctx, t, 0.05, ['Hay 3 formas de decir', 'lo que te molesta...'], 410, 108, 'l1', cps=30)
    segs = [('y solo una ', INK), ('cuida a los dos.', TERRA)]
    r = say(ctx, t, 2.6, segs, 650, 'l2', size=92, cps=26)
    if r and t > 3.9:
        x0, tot, f = r
        a, b = seg_span(segs, 1, f)
        underline(ctx, x0 + a + 4, x0 + b - 10, 676, 'ul1', upto=ease((t - 3.9) / 0.35), color=TERRA)


def s_pasiva(ctx, t):
    draw_bg(ctx, 'pasiva')
    ground_line(ctx, 'pasiva')
    label(ctx, t, 0.1, 1, 'Pasiva', SLATE, 'lab1')
    say(ctx, t, 0.7, 'Me callo para no pelear.', 395, 'p1')

    shrink = kf(t, [(1.3, 0.0), (2.1, 1.0)])
    A = charA(s=kf(t, [(1.3, 1.1), (2.1, 1.03), (10, 0.97)]), squash=1 - 0.08 * shrink,
              brow=0.45 + 0.4 * shrink, mouth=-0.1 * shrink, wavy=0.7 + 0.3 * shrink,
              look=(4 - 4 * shrink, 7 * shrink), blush=0.55 - 0.25 * shrink,
              mouth_open=talk(t, 11, 0.15, 0.3) if 2.1 < t < 3.0 else 0.0,
              arms=('shy', 'shy') if shrink > 0.5 else ('rest', 'rest'))
    talking = t < 5.0
    B = charB(eyes='happy' if talking else 'dot', mouth=0.6, look=(-3, 0),
              mouth_open=talk(t) if talking else 0.0,
              arms=(('open', 'rest') if math.sin(t * 5) > 0 else ('rest', 'open')) if talking else ('rest', 'rest'))

    r = kf(t, [(0, 52), (3, 62), (6, 98), (9, 132), (12, 140)])
    cy = kf(t, [(0, 880), (9, 830)])
    cloud(ctx, 290, cy, r, 'cloud', dark=kf(t, [(2, 0.15), (10, 0.85)]), swirls=1 + int(r / 38),
          rain=kf(t, [(7.6, 0.0), (8.6, 1.0)]), t=t)
    draw_char(ctx, A, 'A')
    draw_char(ctx, B, 'B')
    bubble(ctx, 730, 800, 300, 140, (690, 1010), 'bla', scale=1.0 if t < 5.0 else pop(t, -1, 5.0),
           lines=['bla bla bla...'], fnt=font(HAND, 58), reveal=((t + 5.6) * 13) % 22)
    bubble(ctx, 480, 880, 300, 165, (370, 1010), 'callo', scale=pop(t, 2.0, 5.2),
           lines=['No, nada...', 'seguí vos.'], fnt=font(HAND, 56), reveal=(t - 2.15) * 24)

    say(ctx, t, 5.4, 'Pero lo que no digo...', 530, 'p2')
    segs = [('se acumula.', SLATE)]
    rr = say(ctx, t, 6.7, segs, 640, 'p3', size=100)
    if rr and t > 7.3:
        x0, tot, f = rr
        underline(ctx, x0 + 4, x0 + tot - 10, 665, 'ul2', upto=ease((t - 7.3) / 0.35), color=SLATE)


def s_agresiva(ctx, t):
    draw_bg(ctx, 'agresiva')
    ground_line(ctx, 'agresiva')
    label(ctx, t, 0.1, 2, 'Agresiva', TERRA, 'lab2')
    say(ctx, t, 0.7, 'Lo digo... pero atacando.', 395, 'a1')

    boom = kf(t, [(1.8, 0.0), (2.3, 1.0), (6.4, 1.0), (7.2, 0.0)])
    shouting = 2.3 < t < 5.4
    if t < 1.8:     # still swallowing it, like in the last scene
        A = charA(s=0.97, squash=0.92, look=(0, 7), brow=0.85, wavy=1.0, mouth=-0.1, blush=0.3,
                  arms=('shy', 'shy'))
    elif t < 6.4:   # explodes
        A = charA(s=0.97 + 0.23 * boom, squash=0.92 + 0.14 * boom, lean=0.07 * boom, look=(5 * boom, 0),
                  brow=-1.0 * boom + 0.85 * (1 - boom), mouth=-0.7, eyes='dot',
                  mouth_open=talk(t, 16, 0.65, 1.0) if shouting else 0.0,
                  arms=('fist', 'point') if boom > 0.5 else ('shy', 'shy'),
                  anger=boom, shake=3.0 if shouting else 0.0, blush=0.3 + 0.4 * boom)
    else:           # ...and regrets it
        A = charA(s=1.05 + 0.15 * boom, squash=1 + 0.06 * boom, look=(2, 6), brow=0.8 - 1.8 * boom,
                  mouth=-0.45, anger=boom, blush=0.4, arms=('rest', 'rest'))
    scared = t > 2.6
    bx, ph = walk(t, 3.9, 5.6, 690, 800)
    B = charB(x=bx, walk=ph, s=kf(t, [(3.9, 1.1), (5.6, 0.97)]),
              eyes='wide' if 2.6 < t < 6.0 else 'dot', brow=0.9 if scared else None,
              mouth=-0.4 if scared else 0.5, mouth_open=0.35 if 2.6 < t < 4.5 else 0.0,
              lean=-0.15 if 2.6 < t < 4.0 else (-0.05 if scared else 0.0),
              sweat=1.0 if scared else 0.0, look=(-4, 0) if t < 6 else (-6, 3),
              arms=('guard', 'guard') if 2.6 < t < 5.6 else (('shy', 'shy') if scared else ('rest', 'rest')))

    cloud(ctx, 290, 830, kf(t, [(1.8, 140), (2.3, 150), (7, 150), (9, 125)]), 'cloud',
          dark=kf(t, [(1.8, 0.85), (2.3, 1.0), (8, 0.8)]), swirls=5, t=t,
          bolt=1.0 if (shouting and (int(t * 15) // 2) % 3 != 0) else 0.0)
    # the bond cracks
    if t > 4.0:
        xs = np.linspace(430, 640, 12)
        ys = GROUND_Y + 4 + np.where(np.arange(12) % 2 == 0, -9, 9)
        ctx.line(np.stack([xs, ys], 1), 5.0, key='crack', upto=ease((t - 4.0) / 0.6), taper=(0.1, 0.1))
    draw_char(ctx, A, 'A')
    draw_char(ctx, B, 'B')
    bubble(ctx, 590, 790, 440, 250, (420, 1070), 'grito', kind='spiky', fill=rgb('#F5CBB8'),
           scale=pop(t, 2.2, 6.0), lines=['¡NUNCA ME', 'DEJÁS HABLAR!'], fnt=font(BRUSH, 70),
           color=rgb('#A33A2B'), reveal=(t - 2.3) * 40, shake=2.5 if shouting else 0.0)

    segs = [('Me escucha... ', INK), ('pero se aleja.', TERRA)]
    say(ctx, t, 5.4, segs, 530, 'a2')


def s_asertiva(ctx, t):
    draw_bg(ctx, 'asertiva')
    ground_line(ctx, 'asertiva')
    label(ctx, t, 0.1, 3, 'Asertiva', SAGE_D, 'lab3')
    say_lines(ctx, t, 0.7, ['Digo lo que siento', 'y lo que necesito,', [('con respeto.', SAGE_D)]], 395, 104, 'as1')

    ax, aph = walk(t, 6.6, 8.2, 290, 322)
    bx, bph = walk(t, 6.8, 8.2, 690, 658)
    calm = t > 2.9
    together = t > 8.2
    hand_pt = ((ax + bx) / 2, 1300)
    armsA = ('chest', 'open') if 2.9 < t < 6.6 else ('rest', 'rest')
    if t > 6.9:
        armsA = ('rest', ('abs', hand_pt[0] - 12, hand_pt[1], 0.1))
    A = charA(x=ax, walk=aph, brow=0.3 if not calm else 0.1, look=(4, 0),
              mouth=0.35 if not together else 0.9, eyes='happy' if together else 'dot',
              mouth_open=talk(t, 11, 0.2, 0.4) if 3.1 < t < 4.7 else 0.0, arms=armsA)
    nod = -7 * math.sin((t - 4.6) * 9) if 4.6 < t < 5.7 else 0.0
    armsB = ('rest', 'rest')
    if t > 7.1:
        armsB = (('abs', hand_pt[0] + 12, hand_pt[1], -0.1), 'rest')
    B = charB(x=bx, walk=bph, bob=nod, eyes='closed' if 4.6 < t < 5.8 else ('happy' if together else 'dot'),
              brow=0.2 if t > 4.6 else None, mouth=0.8 if t > 4.6 else 0.45, look=(-4, 0),
              mouth_open=talk(t, 11, 0.2, 0.4) if 5.3 < t < 6.2 else 0.0, arms=armsB)

    k = kf(t, [(3.4, 0.0), (8.0, 1.0)])
    cloud(ctx, 290 - 90 * k, 830 - 150 * k, 92 - 60 * k, 'cloud', dark=0.45 * (1 - k), swirls=max(1, int(3 - 3 * k)),
          alpha=1 - ease((t - 6.8) / 1.4), t=t)
    draw_char(ctx, A, 'A')
    draw_char(ctx, B, 'B')
    heart(ctx, hand_pt[0], kf(t, [(8.4, 1000), (12, 960)]) + 5 * math.sin(t * 3),
          34 * pop(t, 8.4, dur=0.35), 'heart')
    bubble(ctx, 420, 850, 420, 170, (365, 985), 'pedido', scale=pop(t, 3.1, 6.6),
           lines=['¿Me dejás terminar', 'la idea?'], fnt=font(HAND, 60), reveal=(t - 3.25) * 26)
    bubble(ctx, 775, 745, 270, 115, (705, 990), 'dale', scale=pop(t, 5.2, 7.4),
           lines=['¡Perdón! Dale.'], fnt=font(HAND, 56), reveal=(t - 5.35) * 24)

    say_lines(ctx, t, 8.5, ['Me cuido a mí...', [('y cuido el vínculo.', SAGE_D)]], 745, 106, 'as2')


def s_formula(ctx, t):
    draw_bg(ctx, 'formula')
    say(ctx, t, 0.05, '¿Cómo se hace?', 250, 'f0', size=110, name=BRUSH, color=TERRA, weight=0.8, cps=24)
    say(ctx, t, 0.6, 'Probá con estos 3 pasos:', 352, 'f1', size=80)

    cv = ctx.cv
    slide = kf(t, [(0.25, 1100.0), (0.95, 0.0)], 'o')
    ang = kf(t, [(0.25, 6.0), (1.1, -1.3)], 'o')
    cv.save()
    cv.translate(540, 925 + slide)
    cv.rotate(ang)
    cv.translate(-540, -925)
    x0c, x1c, y0c, y1c = 88, 992, 440, 1410
    card = np.array([[x0c, y0c], [x1c, y0c], [x1c, y1c], [x0c, y1c]], np.float64)
    card = np.vstack([np.linspace(card[i], card[(i + 1) % 4], 20, endpoint=False) for i in range(4)])
    # soft shadow
    sh = skia.Paint(AntiAlias=True)
    sh.setColor4f(rgb('#7A6A55', 0.28))
    sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 14))
    cv.drawRect(skia.Rect.MakeLTRB(x0c + 10, y0c + 16, x1c + 8, y1c + 18), sh)
    ctx.solid(card, rgb('#FBF7EC'), key='card', amp=1.2)
    for j, ly in enumerate(range(y0c + 110, y1c - 20, 64)):
        ctx.line([[x0c + 8, ly], [x1c - 8, ly]], 2.4, color=rgb('#9DB5CF'), key=('rule', j), alpha=0.75,
                 amp=0.7, taper=(0.02, 0.02))
    ctx.line([[190, y0c + 6], [190, y1c - 6]], 2.6, color=rgb('#D98C86'), key='margin', alpha=0.8, amp=0.7,
             taper=(0.01, 0.01))
    ctx.loop(card, 3.2, key='cardl', amp=0.8, alpha=0.5, overshoot=0.02)
    # masking tape
    for j, (tx, ty, ta) in enumerate([(150, 452, -32), (930, 450, 28)]):
        cv.save()
        cv.translate(tx, ty)
        cv.rotate(ta)
        tp = np.array([[-70, -22], [70, -22], [74, -8], [68, 6], [72, 22], [-70, 22], [-66, 8], [-72, -6]], np.float64)
        ctx.wash(tp, rgb('#E6D5B0'), key=('tape', j), amp=1.0, edge=0.2, alpha=0.85, blend=skia.BlendMode.kSrcOver)
        cv.restore()

    steps = [
        ('lo que pasó (sin juzgar)', ['Cuando me interrumpís,']),
        ('lo que sentís', ['me frustra.']),
        ('lo que necesitás', ['¿Me dejás terminar', 'la idea?']),
    ]
    sent_font = min((fit_font(HAND, 92, [(s, INK)], 740) for _, ss in steps for s in ss), key=lambda f: f.getSize())
    for k, (lab, sent) in enumerate(steps):
        ts = 1.3 + k * 2.3
        yl = 572 + k * 250
        if t < ts:
            continue
        scribble_circle(ctx, 145, yl + 28, 40, 44, ('nc', k), upto=ease((t - ts) / 0.3), color=TERRA, width=5.5)
        lettering(ctx, str(k + 1), 145, yl + 56, font(BRUSH, 80), ('n', k), reveal=(t - ts - 0.1) * 20, color=TERRA)
        lettering(ctx, lab, 225, yl, font(BRUSH, 64), ('lab', k), reveal=(t - ts - 0.2) * 34, align='left',
                  color=TERRA)
        done = 0
        for j, ln in enumerate(sent):
            lettering(ctx, ln, 225, yl + 104 + j * 92, sent_font, ('s', k, j), reveal=(t - ts - 0.85) * 24 - done,
                      align='left', weight=1.7)
            done += len(ln)
    if t > 9.0:
        segs = [('tip: ', TERRA), ('evitá el "siempre" y el "nunca".', INK)]
        f = fit_font(HAND, 62, segs, 800)
        lettering(ctx, segs, 540, 1368, f, 'tip', reveal=(t - 9.0) * 30, weight=1.3)
    cv.restore()


def s_cierre(ctx, t):
    draw_bg(ctx, 'cierre')
    xs = np.linspace(-20, W + 20, 60)
    ctx.line(np.stack([xs, _hill_y(xs)], 1), 5.0, key='hillcl', taper=(0.02, 0.02), amp=1.4)
    mx = np.linspace(560, W + 20, 40)
    ctx.line(np.stack([mx, 1085 - 150 * np.exp(-((mx - 800) / 190) ** 2) - 70 * np.exp(-((mx - 1000) / 150) ** 2)], 1),
             4.0, key='mtl', alpha=0.75, taper=(0.3, 0.02), amp=1.2)
    for j in range(5):  # little sea glints
        gx, gy = 120 + j * 190 + (j % 2) * 40, 1150 + (j % 3) * 45
        ctx.line([[gx, gy], [gx + 40, gy + 1]], 3.4, key=('glint', j), alpha=0.5, color=rgb('#F3E7C8'))

    ax, bx = 420, 662
    hy = _hill_y(np.array([ax, bx]))
    hand = ((ax + bx) / 2, min(hy) - 40)
    A = charA(x=ax, y=hy[0] + 2, s=0.82, sit=True, eyes='closed', mouth=0.8, look=(3, 0),
              arms=('rest', ('abs', hand[0] - 9, hand[1], 0.1)), legs_swing=math.sin(t * 3.2))
    B = charB(x=bx, y=hy[1] + 2, s=0.82, sit=True, eyes='closed', mouth=0.8, look=(-3, 0),
              arms=(('abs', hand[0] + 9, hand[1], -0.1), 'rest'), legs_swing=math.sin(t * 3.2 + 1.9))
    cloud(ctx, kf(t, [(0, 860), (6, 960)]), 700, 20, 'cloud', dark=0.0, swirls=1, alpha=0.55 * (1 - ease(t / 5)))
    draw_char(ctx, A, 'A')
    draw_char(ctx, B, 'B')
    heart(ctx, hand[0], hand[1] - 250 + 6 * math.sin(t * 2.5), 24 * pop(t, 0.6, dur=0.4), 'heart2')

    end = say_lines(ctx, t, 0.15, ['Se trata de decir', 'lo que sentís', 'sin lastimar...'], 360, 104, 'c1', cps=28)
    segs = [('y sin lastimarte.', TERRA)]
    r = say(ctx, t, 2.9, segs, 700, 'c2', size=112, cps=22)
    if r and t > 3.8:
        x0, tot, f = r
        underline(ctx, x0 + 6, x0 + tot - 12, 728, 'ul3', upto=ease((t - 3.8) / 0.35), color=TERRA)
    rr = say(ctx, t, 4.5, 'guardalo para cuando lo necesites', 850, 'cta', size=52, name=BRUSH, color=TAG,
             weight=0, cps=40)


SCENES = [s_hook, s_pasiva, s_agresiva, s_asertiva, s_formula, s_cierre]

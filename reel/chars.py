"""The two little characters, speech bubbles, the worry-cloud and small doodles."""
import math
from dataclasses import dataclass, field

import numpy as np
import skia

from draw import (INK, Ctx, font, glyph_count, hseed, lettering, mix, rgb, shade, text_width,
                  textured_paint, with_alpha)

BLUE = rgb('#86A7D2')
CORAL = rgb('#EC9A78')
CHEEK = rgb('#F0917F')
LEAF = rgb('#9DB77E')
MOUTH = rgb('#7A3B36')

RX, RY, LEG = 112.0, 128.0, 84.0


@dataclass
class Char:
    name: str
    x: float
    y: float = 1400.0          # ground line under the feet
    s: float = 1.1
    color: skia.Color4f = field(default_factory=lambda: BLUE)
    hair: str = 'tuft'
    lean: float = 0.0          # radians, positive leans right
    squash: float = 1.0
    bob: float = 0.0
    eyes: str = 'dot'          # dot | happy | closed | wide
    look: tuple = (0.0, 0.0)
    brow: float = None         # -1 angry .. +1 worried
    mouth: float = 0.5         # -1 frown .. +1 smile
    mouth_open: float = 0.0
    wavy: float = 0.0
    arms: tuple = ('rest', 'rest')
    walk: float = None         # walking phase (radians) or None
    sit: bool = False
    blush: float = 0.55
    sweat: float = 0.0
    anger: float = 0.0
    shake: float = 0.0
    legs_swing: float = 0.0


def _ellipse(cx, cy, rx, ry, n=64, a0=0.0):
    th = np.linspace(0, 2 * np.pi, n, endpoint=False) + a0
    return np.stack([cx + rx * np.cos(th), cy + ry * np.sin(th)], 1)


def body_outline(n=180):
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    x = RX * (1 + 0.06 * np.sin(th)) * np.cos(th)
    y = RY * np.sin(th)
    return np.stack([x, y - RY + 10], 1)  # pivot (0,0) at the hips


def draw_char(ctx: Ctx, c: Char, key):
    s = c.s
    X, Y = c.x, c.y
    if c.shake:
        r = np.random.default_rng(hseed(key, 'shake', int(ctx.t * 15)))
        X += (r.random() - 0.5) * 2 * c.shake
    sq = c.squash
    ca, sa = math.cos(c.lean), math.sin(c.lean)
    hip_y = -LEG if not c.sit else -18

    def T(p):
        p = np.atleast_2d(np.asarray(p, np.float64))
        x = p[:, 0] / math.sqrt(sq)
        y = p[:, 1] * sq
        xr = x * ca - y * sa
        yr = x * sa + y * ca
        return np.stack([X + s * xr, Y + s * (hip_y + yr + c.bob)], 1)

    cen = np.array([0.0, -RY + 10])
    lw = 6.2 * s

    # ---- legs (drawn first so the body sits on top)
    for sgn in (-1, 1):
        hip = T([sgn * 40, -3])[0]
        if c.sit:
            sw = c.legs_swing * sgn
            knee = hip + np.array([sgn * 6 * s, 30 * s])
            foot = hip + np.array([sgn * 10 * s + sw * 10 * s, 62 * s])
            ctx.line([hip, knee, foot], lw, key=(key, 'leg', sgn), taper=(0.05, 0.05))
            ctx.line([foot, foot + np.array([sgn * 18 * s, 2 * s])], lw, key=(key, 'ft', sgn))
            continue
        fx = X + s * sgn * 44
        fy = Y
        if c.walk is not None:
            ph = c.walk + (0 if sgn < 0 else math.pi)
            fx += s * 14 * math.cos(ph)
            fy -= s * 16 * max(0.0, math.sin(ph))
        mid = (hip + np.array([fx, fy])) / 2 + np.array([sgn * 2 * s, 0])
        ctx.line([hip, mid, [fx, fy]], lw, key=(key, 'leg', sgn), taper=(0.05, 0.05))
        ctx.line([[fx - sgn * 4 * s, fy], [fx + sgn * 20 * s, fy + 1]], lw * 1.05, key=(key, 'ft', sgn))

    # ---- body
    ol = T(body_outline())
    ctx.under(ol, key=(key, 'body'))
    ctx.wash(ol, c.color, key=(key, 'body'), amp=3.5)
    # cheeks
    eye_y = cen[1] - 16
    lk = np.array(c.look)
    for sgn in (-1, 1):
        if c.blush > 0:
            ch = T(_ellipse(sgn * 62 + lk[0] * 0.5, cen[1] + 16, 20, 13, 28))
            ctx.wash(ch, CHEEK, key=(key, 'cheek', sgn), alpha=c.blush, edge=0.15, amp=1.5,
                     blend=skia.BlendMode.kSrcOver)
    ctx.loop(ol, lw * 1.05, key=(key, 'bodyline'))

    # ---- hair
    top = np.array([0.0, -2 * RY + 10])
    if c.hair == 'tuft':
        for j, (dx, h, cu) in enumerate([(-14, 30, -1), (0, 38, 1), (14, 28, 1)]):
            t = np.linspace(0, 1, 12)
            pts = np.stack([top[0] + dx + cu * 10 * np.sin(t * 2.6) * t, top[1] + 4 - h * t], 1)
            ctx.line(T(pts), lw * 0.85, key=(key, 'hair', j), taper=(0.05, 0.5), amp=0.8)
    elif c.hair == 'sprout':
        t = np.linspace(0, 1, 14)
        stem = np.stack([top[0] + 4 + 6 * np.sin(t * 2.2), top[1] + 4 - 44 * t], 1)
        tip = stem[-1]
        for sgn, ang in ((-1, -2.5), (1, -0.55)):
            L = 30
            d = np.array([math.cos(ang), math.sin(ang)])
            nrm = np.array([-d[1], d[0]])
            u = np.linspace(0, 1, 16)
            a = tip + d[None, :] * (u * L)[:, None] + nrm[None, :] * (np.sin(u * np.pi) * 11)[:, None]
            b = tip + d[None, :] * (u * L)[::-1, None] - nrm[None, :] * (np.sin(u[::-1] * np.pi) * 11)[:, None]
            leaf = np.vstack([a, b])
            ctx.under(T(leaf), key=(key, 'leaf', sgn))
            ctx.wash(T(leaf), LEAF, key=(key, 'leaf', sgn), amp=1.5, edge=0.4)
            ctx.loop(T(leaf), lw * 0.7, key=(key, 'leafl', sgn), amp=0.8)
        ctx.line(T(stem), lw * 0.8, key=(key, 'stem'), taper=(0.05, 0.2), amp=0.8)

    # ---- face
    for sgn in (-1, 1):
        e = np.array([sgn * 34, eye_y]) + lk
        if c.eyes == 'dot':
            ctx.dot(T(e)[0], 7.2 * s, ry=9.2 * s, key=(key, 'eye', sgn))
        elif c.eyes == 'wide':
            ctx.loop(T(_ellipse(e[0], e[1], 13, 14, 24)), lw * 0.7, key=(key, 'eyew', sgn), amp=0.6)
            ctx.dot(T(e + np.array([0, 2]))[0], 5.5 * s, key=(key, 'pup', sgn))
        elif c.eyes in ('happy', 'closed'):
            xx = np.linspace(-11, 11, 10)
            k = -9 if c.eyes == 'happy' else 6
            pts = np.stack([e[0] + xx, e[1] + 2 + k * (1 - (xx / 11) ** 2)], 1)
            ctx.line(T(pts), lw * 0.8, key=(key, 'eyea', sgn), taper=(0.2, 0.2), amp=0.6)
        if c.brow is not None:
            b = c.brow
            inner = e + np.array([-sgn * 9, -23 - b * 8])
            outer = e + np.array([sgn * 13, -22 + b * 4])
            ctx.line(T([outer, (outer + inner) / 2 + np.array([0, -2]), inner]), lw * 0.75,
                     key=(key, 'brow', sgn), taper=(0.2, 0.2), amp=0.5)

    m0 = np.array([0.0, cen[1] + 20]) + lk * 0.6
    wm = 16 + 8 * max(0.0, c.mouth_open - 0.4)
    xx = np.linspace(-wm, wm, 16)
    bell = 1 - (xx / wm) ** 2
    up = m0[1] + c.mouth * 9 * bell + c.wavy * 3.2 * np.sin(xx * 0.42)
    if c.mouth_open > 0.05:
        lo = up + c.mouth_open * 28 * bell ** 0.7 + 2
        shape = np.vstack([np.stack([m0[0] + xx, up], 1), np.stack([m0[0] + xx[::-1], lo[::-1]], 1)])
        ctx.wash(T(shape), MOUTH, key=(key, 'mouthf'), amp=0.8, edge=0.1, alpha=0.95)
        ctx.loop(T(shape), lw * 0.7, key=(key, 'mouthl'), amp=0.5, overshoot=0.02)
    else:
        ctx.line(T(np.stack([m0[0] + xx, up], 1)), lw * 0.78, key=(key, 'mouth'), taper=(0.2, 0.2), amp=0.5)

    # ---- arms
    th_s = math.radians(12)
    for i, sgn in enumerate((-1, 1)):
        spec = c.arms[i]
        sh_l = np.array([sgn * RX * math.cos(th_s) * 0.98, cen[1] + RY * math.sin(th_s)])
        S = T(sh_l)[0]
        if isinstance(spec, str):
            spec = ARM_POSES[spec]
        if spec[0] == 'abs':
            Hn = np.array(spec[1:3], np.float64)
            bend = spec[3] if len(spec) > 3 else 0.15
        else:
            dx, dy = spec[0], spec[1]
            bend = spec[2] if len(spec) > 2 else 0.15
            Hn = T(sh_l + np.array([sgn * dx, dy]))[0]
        d = Hn - S
        L = np.hypot(*d) + 1e-6
        nrm = np.array([-d[1], d[0]]) / L
        ctrl = S + d / 2 + nrm * bend * L * (-sgn)
        u = np.linspace(0, 1, 16)[:, None]
        pts = (1 - u) ** 2 * S + 2 * u * (1 - u) * ctrl + u ** 2 * Hn
        ctx.line(pts, lw * 0.95, key=(key, 'arm', sgn), taper=(0.04, 0.05))
        hand = _ellipse(Hn[0], Hn[1], 11 * s, 11 * s, 20)
        ctx.under(hand, key=(key, 'hand', sgn))
        ctx.wash(hand, c.color, key=(key, 'hand', sgn), amp=0.8, edge=0.2)
        ctx.loop(hand, lw * 0.75, key=(key, 'handl', sgn), amp=0.6)

    # ---- extras
    head_top = T(top)[0]
    if c.sweat > 0.01:
        sp = T([RX * 0.95, cen[1] - 60])[0]
        u = np.linspace(0, 2 * np.pi, 30)
        drop = np.stack([np.sin(u) * 12 * (1 - np.cos(u)) / 2 * 1.3, -np.cos(u) * 20], 1)
        drop = sp + drop * s * c.sweat
        ctx.wash(drop, rgb('#A9D0E8'), key=(key, 'sweat'), amp=0.6, edge=0.3)
        ctx.loop(drop, lw * 0.6, key=(key, 'sweatl'), amp=0.4)
    if c.anger > 0.01:
        for j, ang in enumerate((-2.2, -1.75, -1.3)):
            d = np.array([math.cos(ang), math.sin(ang)])
            p0 = head_top + d * 40 * s + np.array([-60 * s, 30 * s])
            p1 = p0 + d * 34 * s * c.anger
            ctx.line([p0, (p0 + p1) / 2 + np.array([3, 0]), p1], lw * 0.8, key=(key, 'ang', j),
                     color=rgb('#B8432F'))
    return {'head_top': head_top, 'mouth': T(m0)[0], 'hands': None}


ARM_POSES = {
    'rest': (22, 80, 0.12),
    'hug': (-150, 40, -0.25),
    'hips': (30, 40, -0.6),
    'up': (40, -70, 0.2),
    'fist': (28, -75, -0.3),
    'point': (88, -18, 0.05),
    'open': (70, 30, 0.2),
    'chest': (-70, 20, -0.3),
    'wave': (45, -95, 0.15),
    'guard': (38, -72, 0.25),
    'shy': (-88, 92, 0.22),
}


# --------------------------------------------------------------------------
# bubbles
# --------------------------------------------------------------------------

def bubble(ctx: Ctx, cx, cy, w, h, tail, key, kind='round', scale=1.0, fill=rgb('#FBF6EA'),
           lines=(), fnt=None, color=INK, reveal=1e9, shake=0.0, text_dy=0.0, spacing=1.0):
    if scale <= 0.01:
        return
    if lines and fnt is not None:
        tw = max(text_width(ln, fnt, spacing) for ln in lines)
        th_ = fnt.getSize() * 1.02 * len(lines)
        pad = 1.45 if kind == 'spiky' else 1.22
        w = max(w, tw * pad + 80)
        h = max(h, th_ * pad + 60)
    n = 90
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    tx, ty = tail
    ta = math.atan2((ty - cy) / h, (tx - cx) / w)
    if kind == 'spiky':
        r = np.random.default_rng(hseed(key, 'spk'))
        k = 22
        th = np.linspace(0, 2 * np.pi, 2 * k, endpoint=False) + r.random() * 0.2
        rr = np.where(np.arange(2 * k) % 2 == 0, 1.12, 0.84) + (r.random(2 * k) - 0.5) * 0.12
    else:
        rr = 1 + 0.03 * np.sin(th * 3 + 1)
    pts = np.stack([cx + w / 2 * rr * np.cos(th), cy + h / 2 * rr * np.sin(th)], 1)
    # splice in the tail
    dth = 0.22 if kind != 'spiky' else 0.3
    diff = (th - ta + np.pi) % (2 * np.pi) - np.pi
    keep = np.abs(diff) > dth
    idx = np.where(keep)[0]
    # rotate so the gap is at the end
    first = idx[np.argmax(diff[idx] > 0)] if np.any(diff[idx] > 0) else idx[0]
    order = np.roll(np.arange(n if kind != 'spiky' else len(th)), -first)
    order = [i for i in order if keep[i]]
    poly = np.vstack([pts[order], [[tx, ty]]])
    if scale != 1.0:
        poly = np.array([cx, cy]) + (poly - np.array([cx, cy])) * scale
    if shake:
        rs = np.random.default_rng(hseed(key, int(ctx.t * 15)))
        poly = poly + (rs.random(2) - 0.5) * 2 * shake
    ctx.solid(poly, fill, key=(key, 'fill'), amp=1.5, alpha=0.97)
    ctx.loop(poly, 5.6, key=(key, 'line'), amp=1.2, overshoot=0.05, start=0.0)
    if scale > 0.85 and lines:
        lh = fnt.getSize() * 1.02
        y0 = cy - lh * (len(lines) - 1) / 2 + fnt.getSize() * 0.32 + text_dy
        done = 0
        for i, ln in enumerate(lines):
            lettering(ctx, ln, cx, y0 + i * lh, fnt, (key, 'txt', i), reveal=reveal - done,
                      color=color, shake=shake, rot=2.5, spacing=spacing)
            done += glyph_count(ln)


# --------------------------------------------------------------------------
# the worry cloud ("la molestia")
# --------------------------------------------------------------------------

def cloud(ctx: Ctx, cx, cy, r, key, dark=0.0, rain=0.0, bolt=0.0, alpha=1.0, swirls=2, t=0.0,
          bolt_dir=1):
    if r < 2 or alpha <= 0.01:
        return
    n = 160
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    bumps = 7
    rr = 0.84 + 0.2 * np.abs(np.cos(th * bumps / 2 + 0.4)) ** 0.8
    pts = np.stack([cx + r * 1.25 * rr * np.cos(th), cy + r * 0.82 * rr * np.sin(th)], 1)
    base = mix(rgb('#A6B1C4'), rgb('#6C7389'), dark)
    if alpha > 0.95:
        ctx.under(pts, key=(key, 'fill'))
    ctx.wash(pts, base, key=(key, 'fill'), amp=3, alpha=alpha)
    ctx.loop(pts, 5.5, key=(key, 'line'), amp=1.4, alpha=alpha)
    rng = np.random.default_rng(hseed(key, 'sw'))
    spots = [(-0.45, -0.05), (0.35, 0.1), (0.0, -0.3), (-0.1, 0.3), (0.55, -0.25), (-0.6, 0.25)]
    for j in range(min(swirls, len(spots))):
        sx, sy = spots[j]
        u = np.linspace(0, 1, 40)
        ang = u * 4.2 * np.pi + rng.random() * 6
        rad = r * (0.05 + 0.2 * u)
        sp = np.stack([cx + sx * r + rad * np.cos(ang) * 1.1, cy + sy * r * 0.7 + rad * np.sin(ang) * 0.8], 1)
        ctx.line(sp, 3.8, key=(key, 'sw', j), alpha=0.55 * alpha, amp=0.8, taper=(0.3, 0.3))
    if rain > 0.01:
        for j in range(9):
            rx = cx + (j / 8 - 0.5) * r * 1.9 + (rng.random() - 0.5) * 20
            ph = (t * 1.6 + rng.random()) % 1.0
            y0 = cy + r * 0.75 + ph * 120
            a = alpha * rain * (1 - ph)
            ctx.line([[rx, y0], [rx - 5, y0 + 22]], 4.2, key=(key, 'rain', j), alpha=a, color=rgb('#5E7596'))
    if bolt > 0.01:
        bx, by = cx + bolt_dir * r * 0.5, cy + r * 0.6
        zz = np.array([[0, 0], [22, 50], [4, 52], [34, 110], [-6, 44], [14, 42], [-10, 0]], np.float64)
        zz[:, 0] *= bolt_dir
        zz = zz * bolt + np.array([bx, by])
        ctx.wash(zz, rgb('#F2C14E'), key=(key, 'bolt'), amp=1.2, edge=0.3, blend=skia.BlendMode.kSrcOver)
        ctx.loop(zz, 4.6, key=(key, 'boltl'), amp=0.8, overshoot=0.02)


def heart(ctx: Ctx, cx, cy, size, key, color=rgb('#D9604F'), alpha=1.0):
    if size < 1:
        return
    t = np.linspace(0, 2 * np.pi, 80, endpoint=False)
    x = 16 * np.sin(t) ** 3
    y = -(13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t))
    pts = np.stack([cx + x * size / 16, cy + y * size / 16], 1)
    ctx.wash(pts, color, key=(key, 'f'), amp=1.5, alpha=alpha, blend=skia.BlendMode.kSrcOver)
    ctx.loop(pts, max(3.0, size / 7), key=(key, 'l'), amp=0.8, alpha=alpha)


def scribble_circle(ctx: Ctx, cx, cy, rx, ry, key, upto=1.0, color=INK, width=5.0):
    th = np.linspace(0, 2 * np.pi * 1.12, 70) - 2.0
    rr = 1 + 0.06 * np.sin(th * 1.5)
    pts = np.stack([cx + rx * rr * np.cos(th), cy + ry * rr * np.sin(th)], 1)
    pts[-12:] += np.linspace(0, 1, 12)[:, None] * np.array([6, -8])
    ctx.line(pts, width, key=key, upto=upto, color=color, taper=(0.05, 0.2), amp=1.0)


def underline(ctx: Ctx, x0, x1, y, key, upto=1.0, color=INK, width=6.0):
    xs = np.linspace(x0, x1, 30)
    ys = y + 5 * np.sin(np.linspace(0, 3, 30)) * np.linspace(0.3, 1, 30)
    ctx.line(np.stack([xs, ys], 1), width, key=key, upto=upto, color=color, taper=(0.1, 0.35), amp=1.2)

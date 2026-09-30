"""Five alternative character families, each drawn from one of the reference posts:
balloons with faces, little hearts with legs, clouds, colored-pencil people and hands."""
import math

import numpy as np
import skia

from draw import INK, PAPER, Ctx, hseed, mix, poly_path, rgb, shade, textured_paint, wobble, with_alpha
from chars import CHEEK, MOUTH

# --------------------------------------------------------------------------
# geometry helpers
# --------------------------------------------------------------------------


def ell(cx, cy, rx, ry, n=48, a0=0.0):
    th = np.linspace(0, 2 * np.pi, n, endpoint=False) + a0
    return np.stack([cx + rx * np.cos(th), cy + ry * np.sin(th)], 1)


def chain(pts, radii, cap=8):
    """outline polygon around a polyline with per-vertex radius (a tube / limb)."""
    pts = np.asarray(pts, np.float64)
    radii = np.broadcast_to(np.asarray(radii, np.float64), (len(pts),))
    if len(pts) > 2:
        u = np.linspace(0, 1, 24)
        from scipy.interpolate import interp1d
        s = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(pts, axis=0).T))])
        s /= s[-1]
        kind = 'quadratic' if len(pts) == 3 else 'cubic'
        pts = np.stack([interp1d(s, pts[:, 0], kind=kind)(u), interp1d(s, pts[:, 1], kind=kind)(u)], 1)
        radii = np.interp(u, s, radii)
    d = np.gradient(pts, axis=0)
    nrm = np.stack([-d[:, 1], d[:, 0]], 1) / (np.hypot(d[:, 0], d[:, 1])[:, None] + 1e-9)
    left = pts + nrm * radii[:, None]
    right = pts - nrm * radii[:, None]
    a1 = math.atan2(nrm[-1, 1], nrm[-1, 0])
    capE = [pts[-1] + radii[-1] * np.array([math.cos(a1 - math.pi * k / cap), math.sin(a1 - math.pi * k / cap)])
            for k in range(1, cap)]
    a0 = math.atan2(-nrm[0, 1], -nrm[0, 0])
    capS = [pts[0] + radii[0] * np.array([math.cos(a0 - math.pi * k / cap), math.sin(a0 - math.pi * k / cap)])
            for k in range(1, cap)]
    return np.vstack([left, capE, right[::-1], capS])


def rot(pts, ang, origin):
    c, s = math.cos(ang), math.sin(ang)
    p = np.asarray(pts, np.float64) - origin
    return np.stack([p[:, 0] * c - p[:, 1] * s, p[:, 0] * s + p[:, 1] * c], 1) + origin


def union(polys):
    path = None
    for q in polys:
        pp = poly_path(q)
        path = pp if path is None else skia.Op(path, pp, skia.PathOp.kUnion_PathOp)
    return path


def ink_stroke(ctx, path, width, color=INK, alpha=1.0):
    p = textured_paint(with_alpha(color, alpha), 'ink', ctx.boil, style=skia.Paint.kStroke_Style)
    p.setStrokeWidth(width)
    p.setStrokeJoin(skia.Paint.kRound_Join)
    p.setStrokeCap(skia.Paint.kRound_Cap)
    ctx.cv.drawPath(path, p)


def wash_path(ctx, path, color, key, alpha=1.0, edge=0.5, under=True, mis=(4, 3)):
    cv = ctx.cv
    if under:
        pu = skia.Paint(AntiAlias=True)
        pu.setColor4f(PAPER)
        cv.drawPath(path, pu)
    r = np.random.default_rng(hseed(key, 'mis'))
    q = skia.Path(path)
    q.offset(*((r.random(2) - 0.5) * 2 * np.array(mis)))
    cv.drawPath(q, textured_paint(with_alpha(color, color.fA * alpha), 'pig', ctx.boil // 2 + hseed(key) % 3,
                                  blend=skia.BlendMode.kMultiply))
    if edge > 0:
        cv.save()
        cv.clipPath(q, doAntiAlias=True)
        pe = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=16)
        pe.setColor4f(with_alpha(shade(color, 0.8), edge * alpha))
        pe.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 5))
        pe.setBlendMode(skia.BlendMode.kMultiply)
        cv.drawPath(q, pe)
        cv.restore()


def shape(ctx, polys, color, key, width=5.6, alpha=1.0, edge=0.5, under=True, amp=1.4):
    """filled watercolor silhouette (union of parts) with one hand-inked outline."""
    wob = [wobble(p, (key, i), ctx.boil, amp=amp, freq=1.3, drift=0.6) for i, p in enumerate(polys)]
    path = union(wob)
    wash_path(ctx, path, color, key, alpha=alpha, edge=edge, under=under)
    ink_stroke(ctx, path, width, alpha=alpha)
    return path


# --------------------------------------------------------------------------
# faces (shared)
# --------------------------------------------------------------------------

MOODS = {
    #          eyes     brow   mouth  open  wavy  look
    'neutral': ('dot', None, 0.45, 0.0, 0.0, (0, 0)),
    'talk': ('happy', None, 0.6, 0.45, 0.0, (0, 0)),
    'sad': ('dot', 0.9, -0.1, 0.0, 1.0, (0, 6)),
    'angry': ('dot', -1.0, -0.7, 0.9, 0.0, (0, 0)),
    'scared': ('wide', 1.0, -0.3, 0.35, 0.0, (0, 0)),
    'calm': ('dot', 0.15, 0.35, 0.3, 0.0, (0, 0)),
    'happy': ('happy', None, 0.9, 0.0, 0.0, (0, 0)),
    'peace': ('closed', None, 0.8, 0.0, 0.0, (0, 0)),
}


def face(ctx, c, s, mood, key, look=(0, 0), eye_dx=30, blush=0.55, nose=False, glasses=False, lw=5.4):
    eyes, brow, mouth, mopen, wavy, mlook = MOODS[mood]
    cx, cy = c[0] + (look[0] + mlook[0]) * s, c[1] + (look[1] + mlook[1]) * s
    for sgn in (-1, 1):
        e = np.array([cx + sgn * eye_dx * s, cy - 14 * s])
        if blush > 0:
            ctx.wash(ell(cx + sgn * (eye_dx + 26) * s, cy + 14 * s, 17 * s, 11 * s, 24), CHEEK,
                     key=(key, 'ck', sgn), alpha=blush, edge=0.15, amp=1.2, blend=skia.BlendMode.kSrcOver)
        if eyes == 'dot':
            ctx.dot(e, 6.6 * s, ry=8.4 * s, key=(key, 'e', sgn))
        elif eyes == 'wide':
            ctx.loop(ell(e[0], e[1], 12 * s, 13 * s, 24), lw * 0.75, key=(key, 'ew', sgn), amp=0.5)
            ctx.dot(e + np.array([0, 2 * s]), 5 * s, key=(key, 'ep', sgn))
        else:
            xx = np.linspace(-10, 10, 9) * s
            k = -8 if eyes == 'happy' else 6
            ctx.line(np.stack([e[0] + xx, e[1] + 2 * s + k * s * (1 - (xx / (10 * s)) ** 2)], 1), lw * 0.8,
                     key=(key, 'ea', sgn), taper=(0.2, 0.2), amp=0.5)
        if brow is not None:
            inner = e + np.array([-sgn * 9, -22 - brow * 8]) * s
            outer = e + np.array([sgn * 12, -21 + brow * 4]) * s
            ctx.line([outer, inner], lw * 0.75, key=(key, 'b', sgn), taper=(0.2, 0.2), amp=0.4)
        if glasses:
            ctx.loop(ell(e[0], e[1] + 1 * s, 19 * s, 17 * s, 28), lw * 0.7, key=(key, 'gl', sgn), amp=0.6)
    if glasses:
        ctx.line([[cx - 11 * s, cy - 15 * s], [cx + 11 * s, cy - 15 * s]], lw * 0.6, key=(key, 'glb'), amp=0.3)
    if nose:
        ctx.line([[cx + 2 * s, cy - 6 * s], [cx - 3 * s, cy + 6 * s], [cx + 5 * s, cy + 7 * s]], lw * 0.65,
                 key=(key, 'nose'), taper=(0.1, 0.2), amp=0.4)
    my = cy + (22 if nose else 18) * s
    wm = (15 + 7 * max(0.0, mopen - 0.4)) * s
    xx = np.linspace(-wm, wm, 14)
    bell = 1 - (xx / wm) ** 2
    up = my + mouth * 8 * s * bell + wavy * 3 * s * np.sin(xx / s * 0.45)
    if mopen > 0.05:
        lo = up + mopen * 24 * s * bell ** 0.7 + 2
        m = np.vstack([np.stack([cx + xx, up], 1), np.stack([cx + xx[::-1], lo[::-1]], 1)])
        ctx.wash(m, MOUTH, key=(key, 'mf'), amp=0.6, edge=0.1, alpha=0.95)
        ctx.loop(m, lw * 0.65, key=(key, 'ml'), amp=0.4, overshoot=0.02)
    else:
        ctx.line(np.stack([cx + xx, up], 1), lw * 0.75, key=(key, 'm'), taper=(0.2, 0.2), amp=0.4)


def sweat(ctx, p, s, key):
    u = np.linspace(0, 2 * np.pi, 30)
    drop = np.stack([np.sin(u) * 12 * (1 - np.cos(u)) / 2 * 1.3, -np.cos(u) * 20], 1) * s + p
    ctx.wash(drop, rgb('#A9D0E8'), key=(key, 'sw'), amp=0.5, edge=0.3)
    ctx.loop(drop, 3.4, key=(key, 'swl'), amp=0.4)


def anger_marks(ctx, p, s, key, color=rgb('#B8432F')):
    for j, ang in enumerate((-2.3, -1.85, -1.4)):
        d = np.array([math.cos(ang), math.sin(ang)])
        p0 = p + d * 18 * s
        ctx.line([p0, p0 + d * 30 * s], 5.0, key=(key, 'am', j), color=color)


def tension(ctx, c, r, key, n=10, color=INK):
    for j in range(n):
        a = j / n * 2 * np.pi + 0.3
        d = np.array([math.cos(a), math.sin(a)])
        ctx.line([c + d * r, c + d * (r + 26)], 4.0, key=(key, 'tn', j), color=color, alpha=0.7)


def drizzle(ctx, x0, x1, y, key, t=0.0, color=rgb('#5E7596')):
    rng = np.random.default_rng(hseed(key))
    for j in range(7):
        rx = x0 + (x1 - x0) * j / 6 + (rng.random() - 0.5) * 16
        ph = (t * 1.4 + rng.random()) % 1.0
        yy = y + ph * 90
        ctx.line([[rx, yy], [rx - 4, yy + 20]], 4.0, key=(key, 'dr', j), alpha=1 - ph, color=color)


# --------------------------------------------------------------------------
# 1 · globos (balloon people)
# --------------------------------------------------------------------------

BAL_A = rgb('#5F8FD8')
BAL_B = rgb('#9CC2EC')


def balloon(ctx, x, y, r, color, mood, key, anchor, accessory=None, squash=1.0, flush=0.0, wrinkle=0.0,
            look=(0, 0), tilt=0.0, slack=0.0):
    th = np.linspace(0, 2 * np.pi, 120, endpoint=False)
    rng = np.random.default_rng(hseed(key, 'bshape'))
    rr = r * (1 + 0.035 * np.sin(3 * th + rng.random() * 6) + 0.02 * np.sin(5 * th + rng.random() * 6))
    sn = np.sin(th)
    px = rr * np.cos(th) * (1 - 0.16 * np.clip(sn, 0, 1) ** 2) / math.sqrt(squash)
    py = rr * sn * 1.1 * squash
    pts = rot(np.stack([x + px, y + py], 1), tilt, np.array([x, y]))
    bottom = rot(np.array([[x, y + r * 1.1 * squash]]), tilt, np.array([x, y]))[0]
    shape(ctx, [pts], mix(color, rgb('#E9674E'), flush), (key, 'body'), width=5.2)
    # shine
    ctx.line(rot(np.stack([x - r * 0.55 + 14 * np.cos(np.linspace(3.4, 4.3, 8)) * 3,
                           y - r * 0.2 + 14 * np.sin(np.linspace(3.4, 4.3, 8)) * 3], 1), tilt, np.array([x, y])),
             5.0, color=rgb('#FFFFFF'), alpha=0.55, key=(key, 'shine'), taper=(0.3, 0.3))
    # knot
    k = np.array([[0, 0], [-11, 14], [11, 14]], np.float64) + bottom
    ctx.solid(k, shade(color, 0.85), key=(key, 'knot'), amp=0.6)
    ctx.loop(k, 3.6, key=(key, 'knotl'), amp=0.5)
    # string
    a = bottom + np.array([0, 14])
    b = np.asarray(anchor, np.float64)
    u = np.linspace(0, 1, 30)[:, None]
    mid = (a + b) / 2 + np.array([40 * slack, 0])
    line = (1 - u) ** 2 * a + 2 * u * (1 - u) * mid + u ** 2 * b
    line[:, 0] += 6 * np.sin(u[:, 0] * 9 + hseed(key) % 5)
    ctx.line(line, 2.6, key=(key, 'str'), taper=(0.02, 0.05), amp=1.0)
    if wrinkle > 0:
        for j, sg in enumerate((-1, 1)):
            w0 = np.array([x + sg * r * 0.35, y + r * 0.72 * squash])
            ctx.line([w0, w0 + np.array([sg * 8, -14]), w0 + np.array([sg * 2, -26])], 3.4, key=(key, 'wr', j),
                     alpha=0.6 * wrinkle)
    s = r / 110
    fc = rot(np.array([[x, y - r * 0.05]]), tilt, np.array([x, y]))[0]
    face(ctx, fc, s, mood, (key, 'face'), look=look, nose=True, glasses=accessory == 'glasses', blush=0.4)
    if accessory == 'tuft':
        top = rot(np.array([[x, y - r * 1.08 * squash]]), tilt, np.array([x, y]))[0]
        for j in range(6):
            bx = (j - 2.5) * 12 * s
            u = np.linspace(0, 1, 14)
            curl = np.stack([top[0] + bx + 9 * s * np.sin(u * 5.5) * (1 - u * 0.4),
                             top[1] + 10 * s - 24 * s * u + 7 * s * np.cos(u * 5.5)], 1)
            ctx.line(curl, 4.2, key=(key, 'hr', j), taper=(0.1, 0.4), amp=0.5)
    return bottom


# --------------------------------------------------------------------------
# 2 · corazones (little hearts with legs)
# --------------------------------------------------------------------------

HEART_A = rgb('#C4474A')
HEART_B = rgb('#E98D8F')


def heart_char(ctx, x, yg, s, color, mood, key, lean=0.0, arms=('rest', 'rest'), sit=False, crack=0.0, flame=0.0,
               look=(0, 0), hands_to=(None, None), step=0.0):
    t = np.linspace(0, 2 * np.pi, 140, endpoint=False)
    hx = 16 * np.sin(t) ** 3
    hy = -(13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t))
    k = 7.4 * s
    legl = 0 if sit else 62 * s
    cy = yg - legl - 17 * k + 6 * s
    body = np.stack([x + hx * k * 1.02, cy + hy * k], 1)
    pivot = np.array([x, yg - legl])
    body = rot(body, lean, pivot)

    def R(p):
        return rot(np.atleast_2d(np.asarray(p, np.float64)), lean, pivot)

    # legs + feet
    for sg in (-1, 1):
        hip = R([x + sg * 26 * s, cy + 12.5 * k])[0]
        if sit:
            foot = hip + np.array([sg * 18 * s, 55 * s])
            ctx.line([hip, foot], 6 * s, key=(key, 'leg', sg), taper=(0.05, 0.05))
            ctx.line([foot, foot + np.array([sg * 16 * s, 0])], 6 * s, key=(key, 'ft', sg))
        else:
            fx = x + sg * 34 * s + (step * 30 * s if sg > 0 else 0)
            ctx.line([hip, [(hip[0] + fx) / 2 + sg * 3, (hip[1] + yg) / 2], [fx, yg]], 6 * s, key=(key, 'leg', sg),
                     taper=(0.05, 0.05))
            ctx.line([[fx - sg * 4 * s, yg], [fx + sg * 18 * s, yg + 1]], 6.2 * s, key=(key, 'ft', sg))
    # vessels on top
    parts = [body]
    tubes = []
    for j, (dx, ang, L) in enumerate([(-22, -0.25, 40), (6, 0.05, 50), (30, 0.4, 34)]):
        b0 = np.array([x + dx * s, cy - 6.5 * k])
        d = np.array([math.sin(ang), -math.cos(ang)])
        tb = chain([b0, b0 + d * L * s], [13 * s, 12 * s])
        tubes.append((R(b0 + d * L * s)[0], ang + lean))
        parts.append(R(tb))
    shape(ctx, parts, color, (key, 'body'), width=6 * s)
    for j, (tip, ang) in enumerate(tubes):
        o = rot(ell(tip[0], tip[1], 11 * s, 5 * s, 20), ang, tip)
        ctx.solid(o, shade(color, 0.55), key=(key, 'hole', j), amp=0.5)
        ctx.loop(o, 3.2 * s, key=(key, 'holel', j), amp=0.3)
    # highlight
    hl = R(np.stack([x - 9.5 * k + 22 * s * np.cos(np.linspace(3.5, 4.6, 8)), cy - 3.5 * k + 22 * s * np.sin(np.linspace(3.5, 4.6, 8))], 1))
    ctx.line(hl, 6 * s, color=rgb('#FFFFFF'), alpha=0.5, key=(key, 'hl'), taper=(0.3, 0.3))
    if crack > 0:
        zz = np.array([[0, -95], [-16, -60], [12, -30], [-14, 0], [10, 30], [-4, 60]], np.float64) * s + np.array([x + 2 * s, cy])
        ctx.line(R(zz), 4.2 * s, key=(key, 'crack'), upto=crack, taper=(0.1, 0.3))
    # arms
    for i, sg in enumerate((-1, 1)):
        sh = R([x + sg * 13.5 * k, cy - 1.5 * k])[0]
        spec = arms[i]
        if hands_to[i] is not None:
            hand = np.asarray(hands_to[i], np.float64)
        else:
            off = {'rest': (18, 70), 'up': (34, -60), 'point': (95, -20), 'shy': (-70, 50), 'guard': (30, -55),
                   'open': (65, 20), 'chest': (-75, 5)}[spec]
            hand = sh + np.array([sg * off[0], off[1]]) * s
        mid = (sh + hand) / 2 + np.array([sg * 6, 6]) * s
        ctx.line([sh, mid, hand], 5.6 * s, key=(key, 'arm', sg), taper=(0.04, 0.05))
        ctx.dot(hand, 8.5 * s, key=(key, 'hand', sg))
    face(ctx, R([x - 2 * s, cy - 1 * k])[0], s * 0.95, mood, (key, 'face'), look=look, blush=0.35, eye_dx=28)
    if flame > 0:  # steam puffing out of the vessels, like a kettle
        for j, (tip, ang) in enumerate(tubes):
            d = np.array([math.sin(ang), -math.cos(ang)])
            for q, (dist, rad) in enumerate([(22, 11), (46, 15), (74, 19)]):
                c0 = tip + d * dist * s * flame + np.array([(q % 2 - 0.5) * 10 * s, 0])
                pf = ell(c0[0], c0[1], rad * s, rad * 0.85 * s, 24)
                ctx.wash(pf, rgb('#E4E1DA'), key=(key, 'st', j, q), amp=0.8, edge=0.25, blend=skia.BlendMode.kSrcOver,
                         alpha=0.95)
                ctx.loop(pf, 3.2 * s, key=(key, 'stl', j, q), amp=0.5, alpha=0.8)
    return body


# --------------------------------------------------------------------------
# 3 · nubes (cloud creatures)
# --------------------------------------------------------------------------

CLOUD_A = rgb('#93A6CB')
CLOUD_B = rgb('#F6E6D6')


def cloud_char(ctx, x, y, s, color, mood, key, dark=0.0, rain=0.0, bolt=0.0, arms=((0.4, 1.0), (0.4, 1.0)),
               t=0.0, look=(0, 0), swirl_col=None, hands_to=(None, None), swirls=3):
    col = mix(color, rgb('#59607A'), dark)
    th = np.linspace(0, 2 * np.pi, 180, endpoint=False)
    bumps = 7
    rr = 0.86 + 0.17 * np.abs(np.cos(th * bumps / 2 + 0.5)) ** 0.7
    flat = np.where(np.sin(th) > 0, 0.72, 1.0)
    body = np.stack([x + 150 * s * rr * np.cos(th), y + 100 * s * rr * np.sin(th) * flat], 1)
    parts = [body]
    # little legs
    for sg in (-1, 1):
        parts.append(chain([[x + sg * 50 * s, y + 55 * s], [x + sg * 56 * s, y + 100 * s], [x + sg * 64 * s, y + 118 * s]],
                           [15 * s, 12 * s, 11 * s]))
    # tendril arms
    for i, sg in enumerate((-1, 1)):
        base = np.array([x + sg * 140 * s, y + 10 * s])
        if hands_to[i] is not None:
            tip = np.asarray(hands_to[i], np.float64)
        else:
            ang, ln = arms[i]
            tip = base + np.array([sg * math.cos(ang), math.sin(ang)]) * 62 * s * ln
        mid = (base + tip) / 2 + np.array([0, -18 * s])
        parts.append(chain([base, mid, tip], [17 * s, 13 * s, 12 * s]))
    shape(ctx, parts, col, (key, 'body'), width=5.8 * s, edge=0.55)
    sc = swirl_col or shade(col, 0.7)
    rng = np.random.default_rng(hseed(key, 'sw'))
    for j, (sx, sy) in enumerate([(-0.55, -0.35), (0.5, -0.4), (0.62, 0.15), (-0.1, -0.6), (-0.7, 0.12)][:swirls]):
        u = np.linspace(0, 1, 40)
        ang = u * 4 * np.pi + rng.random() * 6
        rad = 30 * s * (0.1 + 0.9 * u)
        sp = np.stack([x + sx * 150 * s + rad * np.cos(ang), y + sy * 100 * s + rad * np.sin(ang) * 0.8], 1)
        ctx.line(sp, 4.2 * s, key=(key, 'swirl', j), color=sc, alpha=0.8, taper=(0.3, 0.3), amp=0.6)
    face(ctx, (x, y + 8 * s), s * 1.05, mood, (key, 'face'), look=look, blush=0.45)
    if rain > 0:
        drizzle(ctx, x - 110 * s, x + 110 * s, y + 90 * s, (key, 'rain'), t=t)
    if bolt > 0:
        zz = np.array([[0, 0], [22, 50], [4, 52], [34, 110], [-6, 44], [14, 42], [-10, 0]], np.float64) * s * bolt
        zz += np.array([x + 70 * s, y + 70 * s])
        ctx.wash(zz, rgb('#F2C14E'), key=(key, 'bolt'), amp=1.0, edge=0.3, blend=skia.BlendMode.kSrcOver)
        ctx.loop(zz, 4.4, key=(key, 'boltl'), amp=0.6, overshoot=0.02)


# --------------------------------------------------------------------------
# 4 · personitas (colored-pencil people)
# --------------------------------------------------------------------------

BOY = dict(skin=rgb('#AFC3DE'), hair=rgb('#34405E'), top=rgb('#6E8FBF'), pants=rgb('#5876A3'), shoes=rgb('#2E3448'))
GIRL = dict(skin=rgb('#F3CBAA'), hair=rgb('#D8672F'), top=rgb('#F3ECDF'), vest=rgb('#8C5B3C'), pants=rgb('#7897C4'),
            shoes=rgb('#5A3526'))


def person(ctx, x, yg, s, who, mood, key, arms=('rest', 'rest'), lean=0.0, look=(0, 0), hands_to=(None, None),
           step=0.0, shrink=0.0):
    P = BOY if who == 'boy' else GIRL
    pivot = np.array([x, yg])

    def R(p):
        return rot(np.atleast_2d(np.asarray(p, np.float64)), lean, pivot)

    sh_y = yg - 300 * s + shrink * 14 * s
    hip_y = yg - 150 * s
    head = np.array([x, sh_y - 78 * s + shrink * 10 * s])
    # legs
    for sg in (-1, 1):
        hip = np.array([x + sg * 30 * s, hip_y])
        foot = np.array([x + sg * 36 * s + (step * 34 * s if sg > 0 else 0), yg - 16 * s])
        knee = (hip + foot) / 2 + np.array([sg * 3 * s, 0])
        shape(ctx, [R(chain([hip, knee, foot], [26 * s, 22 * s, 20 * s]))], P['pants'], (key, 'leg', sg), width=5 * s)
        if who == 'girl':  # rolled-up jeans
            cuff = R(chain([foot + np.array([-24 * s, -8 * s]), foot + np.array([24 * s, -8 * s])], [9 * s]))
            shape(ctx, [cuff], shade(P['pants'], 0.9), (key, 'cuff', sg), width=4 * s)
        shoe = R(ell(foot[0] + sg * 8 * s, yg - 8 * s, 30 * s, 13 * s, 30))
        shape(ctx, [shoe], P['shoes'], (key, 'shoe', sg), width=4.6 * s)
    # torso
    tw, bw = 82 * s, 66 * s
    torso = np.array([[x - tw, sh_y + 16 * s], [x - tw + 14 * s, sh_y], [x + tw - 14 * s, sh_y], [x + tw, sh_y + 16 * s],
                      [x + bw + 4 * s, hip_y + 8 * s], [x - bw - 4 * s, hip_y + 8 * s]], np.float64)
    torso = np.vstack([np.linspace(torso[i], torso[(i + 1) % 6], 12, endpoint=False) for i in range(6)])
    if who == 'boy':
        hood = ell(x, sh_y + 4 * s, 70 * s, 26 * s, 36)
        shape(ctx, [R(torso), R(hood)], P['top'], (key, 'torso'), width=5.4 * s)
        ctx.line(R([[x - 34 * s, hip_y - 38 * s], [x + 34 * s, hip_y - 38 * s]]), 4 * s, key=(key, 'pocket'), alpha=0.7)
        for sg in (-1, 1):
            ctx.line(R([[x + sg * 14 * s, sh_y + 20 * s], [x + sg * 16 * s, sh_y + 62 * s]]), 3.4 * s,
                     key=(key, 'cord', sg), alpha=0.8)
    else:
        shape(ctx, [R(torso)], P['top'], (key, 'torso'), width=5.2 * s)
        for sg in (-1, 1):
            vest = np.array([[x + sg * (tw - 4 * s), sh_y + 14 * s], [x + sg * 26 * s, sh_y + 6 * s],
                             [x + sg * 12 * s, hip_y - 20 * s], [x + sg * (bw + 4 * s), hip_y + 6 * s]], np.float64)
            vest = np.vstack([np.linspace(vest[i], vest[(i + 1) % 4], 10, endpoint=False) for i in range(4)])
            shape(ctx, [R(vest)], P['vest'], (key, 'vest', sg), width=4.6 * s)
    # neck + head
    hc = R(head)[0]
    if who == 'girl':  # long wavy hair behind the head
        th = np.linspace(0, 2 * np.pi, 120, endpoint=False)
        rr = 1 + 0.07 * np.sin(th * 9)
        hair = np.stack([hc[0] + 86 * s * rr * np.cos(th), hc[1] + 30 * s + 110 * s * rr * np.sin(th) * np.where(np.sin(th) > 0, 1.05, 0.72)], 1)
        shape(ctx, [hair], P['hair'], (key, 'hairback'), width=5 * s)
        for j in range(6):
            a = 0.3 + j * 0.45
            c0 = hc + np.array([math.cos(a + 1.2) * 60, 40 + math.sin(a) * 50]) * s
            ctx.line(c0 + np.stack([np.cos(np.linspace(0, 4, 10)) * 8 * s, np.linspace(0, 30, 10) * s], 1), 3.2 * s,
                     key=(key, 'curl', j), alpha=0.6, color=shade(P['hair'], 0.6))
    shape(ctx, [R(chain([[x, sh_y + 4 * s], [x, head[1] + 40 * s]], [16 * s]))], P['skin'], (key, 'neck'), width=4.4 * s)
    if who == 'boy':
        for sg in (-1, 1):
            shape(ctx, [ell(hc[0] + sg * 57 * s, hc[1] + 8 * s, 12 * s, 16 * s, 20)], P['skin'], (key, 'ear', sg),
                  width=4.2 * s)
    hd = ell(hc[0], hc[1], 58 * s, 62 * s, 60)
    shape(ctx, [hd], P['skin'], (key, 'head'), width=5.6 * s)
    if who == 'boy':
        th = np.linspace(np.pi * 1.02, np.pi * 1.98, 30)
        cap = np.stack([hc[0] + 62 * s * np.cos(th), hc[1] - 6 * s + 66 * s * np.sin(th)], 1)
        fringe = [[hc[0] + 60 * s, hc[1] - 14 * s], [hc[0] + 30 * s, hc[1] - 28 * s], [hc[0] + 18 * s, hc[1] - 16 * s],
                  [hc[0] - 4 * s, hc[1] - 30 * s], [hc[0] - 20 * s, hc[1] - 14 * s], [hc[0] - 40 * s, hc[1] - 26 * s],
                  [hc[0] - 60 * s, hc[1] - 12 * s]]
        hairp = np.vstack([cap, fringe])
        shape(ctx, [hairp], P['hair'], (key, 'hair'), width=5 * s)
    else:
        th = np.linspace(np.pi * 1.0, np.pi * 2.0, 30)
        bang = np.vstack([np.stack([hc[0] + 64 * s * np.cos(th), hc[1] - 4 * s + 64 * s * np.sin(th)], 1),
                          [[hc[0] + 62 * s, hc[1] - 4 * s], [hc[0] + 24 * s, hc[1] - 34 * s], [hc[0] - 10 * s, hc[1] - 22 * s],
                           [hc[0] - 44 * s, hc[1] - 30 * s], [hc[0] - 64 * s, hc[1] - 2 * s]]])
        shape(ctx, [bang], P['hair'], (key, 'bang'), width=5 * s)
    face(ctx, hc + np.array([0, 16 * s]), s * 0.9, mood, (key, 'face'), look=look, blush=0.45, eye_dx=24)
    # arms (sleeves) + hands
    for i, sg in enumerate((-1, 1)):
        sh = R([x + sg * (tw - 10 * s), sh_y + 22 * s])[0]
        spec = arms[i]
        if hands_to[i] is not None:
            hand = np.asarray(hands_to[i], np.float64)
            elbow = (sh + hand) / 2 + np.array([sg * 16 * s, 26 * s])
        else:
            e_off, h_off = {
                'rest': ((14, 72), (18, 142)),
                'crossed': ((6, 70), (-62, 44)),
                'point': ((54, 32), (128, 16)),
                'fist': ((52, 56), (64, -14)),
                'guard': ((40, 42), (40, -32)),
                'chest': ((22, 78), (-48, 44)),
                'open': ((34, 70), (90, 80)),
                'shy': ((10, 76), (-40, 132)),
            }[spec]
            elbow = sh + np.array([sg * e_off[0], e_off[1]]) * s
            hand = sh + np.array([sg * h_off[0], h_off[1]]) * s
        top_col = P['top'] if who == 'boy' else P['top']
        shape(ctx, [chain([sh, elbow, hand], [20 * s, 17 * s, 14 * s])], top_col, (key, 'arm', sg), width=5 * s)
        shape(ctx, [ell(hand[0], hand[1], 16 * s, 16 * s, 24)], P['skin'], (key, 'hand', sg), width=4.4 * s)
    return hc


# --------------------------------------------------------------------------
# 5 · manos (hands)
# --------------------------------------------------------------------------

HAND_A = rgb('#DD877B')
HAND_B = rgb('#86A7D2')

GESTURES = {
    # finger (angle deg from 'up', length, curl) for index, middle, ring, pinky; thumb (angle, length)
    'open': ([(-24, 78, 0.0), (-8, 88, 0.0), (8, 84, 0.0), (24, 66, 0.0)], (-78, 60)),
    'relaxed': ([(-16, 74, 0.25), (-4, 82, 0.3), (8, 78, 0.35), (20, 62, 0.4)], (-70, 54)),
    'fist': ([(-20, 30, 1.0), (-6, 32, 1.0), (8, 30, 1.0), (20, 26, 1.0)], (-40, 40)),
    'point': ([(-6, 96, 0.0), (-2, 30, 1.0), (10, 28, 1.0), (22, 24, 1.0)], (-62, 46)),
    'talk': ([(-10, 80, 0.15), (-2, 84, 0.15), (6, 82, 0.15), (14, 70, 0.15)], (-22, 64)),
    'splay': ([(-36, 80, 0.0), (-12, 90, 0.0), (12, 86, 0.0), (36, 68, 0.0)], (-90, 62)),
}


def hand_char(ctx, wrist, ang, s, color, gesture, key, arm_from=None, flip=False, talk_open=0.0, flush=0.0):
    """ang: direction the fingers point (radians, 0 = up). flip mirrors (thumb on the other side)."""
    fingers, thumb = GESTURES[gesture]
    sgn = -1 if flip else 1
    W = np.asarray(wrist, np.float64)
    parts = []
    # palm in local coords (fingers up = -y)
    palm = ell(0, -48 * s, 50 * s, 52 * s, 50)
    parts.append(palm)
    xs = [-33, -11, 11, 31]
    if gesture == 'fist':  # knuckles on top, thumb wrapped across the front
        fingers = []
        palm[:] = ell(0, -50 * s, 52 * s, 44 * s, 50)
        for i in range(4):
            parts.append(ell(xs[i] * s * 1.05, -86 * s, 17 * s, 15 * s, 24))
    for i, (fa, ln, curl) in enumerate(fingers):
        base = np.array([xs[i] * s, -80 * s])
        a = math.radians(fa)
        if gesture == 'talk':
            a -= math.radians(12 * talk_open)
        d = np.array([math.sin(a), -math.cos(a)])
        if curl > 0.5:  # folded finger: short knuckle bump
            parts.append(chain([base + np.array([0, 8 * s]), base + d * ln * 0.4 * s + np.array([0, 10 * s])],
                               [13 * s, 12 * s]))
        else:
            mid = base + d * ln * 0.55 * s
            tipd = np.array([math.sin(a + curl * 0.9), -math.cos(a + curl * 0.9)])
            tip = mid + tipd * ln * 0.45 * s
            parts.append(chain([base, mid, tip], [13.5 * s, 12.5 * s, 11.5 * s]))
    ta, tl = thumb
    thumb_part = None
    if gesture == 'fist':
        thumb_part = chain([[-52 * s, -40 * s], [-20 * s, -62 * s], [14 * s, -66 * s]], [15 * s, 14 * s, 13 * s])
    if gesture == 'talk':
        ta += 40 * talk_open
    a = math.radians(ta)
    tb = np.array([-42 * s, -34 * s])
    d = np.array([math.sin(a), -math.cos(a)])
    if thumb_part is None:
        parts.append(chain([tb, tb + d * tl * 0.6 * s, tb + d * tl * s + np.array([6 * s, 0])], [15 * s, 13.5 * s, 12 * s]))
    # to world
    world = []
    for p in parts:
        q = p.copy()
        q[:, 0] *= sgn
        world.append(rot(q, ang, np.zeros(2)) + W)
    if arm_from is not None:
        A = np.asarray(arm_from, np.float64)
        mid = (A + W) / 2 + np.array([0, 20])
        ctx.line([A, mid, W], 11 * s, key=(key, 'arm'), taper=(0.0, 0.02), amp=1.2)
    col = mix(color, rgb('#E0604F'), flush)
    shape(ctx, world, col, (key, 'hand'), width=6 * s, amp=1.2)

    def to_w(q):
        q = np.asarray(q, np.float64).copy()
        q[:, 0] *= sgn
        return rot(q, ang, np.zeros(2)) + W
    if gesture == 'fist':
        for j in range(3):
            kx = (-22 + j * 22) * s
            ctx.line(to_w([[kx, -96 * s], [kx + 2 * s, -76 * s]]), 3.6 * s, key=(key, 'kn', j), alpha=0.8)
        shape(ctx, [to_w(thumb_part)], col, (key, 'thumb'), width=5.6 * s, amp=0.8)
    return world

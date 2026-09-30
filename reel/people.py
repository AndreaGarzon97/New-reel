"""Improved colored-pencil people (v2): real necks, rounded shoulders, sleeves that join the
body, mitten hands with thumbs, sneakers/boots, noses, brows and fuller hair."""
import math

import numpy as np
import skia

from alt_chars import chain, ell, rot, shape, wash_path, ink_stroke, union
from chars import CHEEK, MOUTH
from draw import INK, PAPER, hseed, mix, rgb, shade, with_alpha, wobble


def spline(pts, closed=True, n=8):
    P = np.asarray(pts, np.float64)
    N = len(P)
    out = []
    rng = range(N) if closed else range(N - 1)
    for i in rng:
        p0 = P[(i - 1) % N] if closed else P[max(i - 1, 0)]
        p1, p2 = P[i], P[(i + 1) % N]
        p3 = P[(i + 2) % N] if closed else P[min(i + 2, N - 1)]
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    if not closed:
        out.append(P[-1])
    return np.array(out)


# --------------------------------------------------------------------------
# palettes / looks
# --------------------------------------------------------------------------

def C(h):
    return rgb(h)


VERSIONS = {
    'v1': {
        'name': 'Azul y pelirroja',
        'boy': dict(kind='boy', skin=C('#F2CFB3'), hair=C('#3A3A48'), hair_style='messy', top=C('#6E8FC2'),
                    top_style='hoodie', pants=C('#4C6591'), shoes=C('#2F3447'), shoe_style='sneaker'),
        'girl': dict(kind='girl', skin=C('#F6D5BD'), hair=C('#D5652E'), hair_style='long', top=C('#F4EEE3'),
                     top_style='vest', vest=C('#8B5A3B'), pants=C('#7B9ACB'), cuffs=True, shoes=C('#4F3024'),
                     shoe_style='boot', freckles=True),
    },
    'v2': {
        'name': 'Salvia y mostaza',
        'boy': dict(kind='boy', skin=C('#B97B55'), hair=C('#231C18'), hair_style='curly', top=C('#DDA73F'),
                    top_style='sweater', pants=C('#5E6B55'), shoes=C('#3B2F27'), shoe_style='sneaker'),
        'girl': dict(kind='girl', skin=C('#8A5A3F'), hair=C('#221A17'), hair_style='curly', top=C('#A9BE92'),
                     top_style='sweater', pants=C('#56688C'), shoes=C('#2E2622'), shoe_style='sneaker',
                     earrings=C('#E2B34A')),
    },
    'v3': {
        'name': 'Lila y coral',
        'boy': dict(kind='boy', skin=C('#F4D9C6'), hair=C('#9A5B34'), hair_style='side', top=C('#A99BD3'),
                    top_style='hoodie', pants=C('#4F5873'), shoes=C('#3A3548'), shoe_style='sneaker', glasses=True),
        'girl': dict(kind='girl', skin=C('#EDC39F'), hair=C('#E3B866'), hair_style='bob', top=C('#EF917B'),
                     top_style='cardigan', inner=C('#F7EFE3'), pants=C('#7F9C8C'), cuffs=True, shoes=C('#6B3E30'),
                     shoe_style='boot'),
    },
}


# --------------------------------------------------------------------------
# face
# --------------------------------------------------------------------------

MOODS = {
    #          eyes     brow   mouth  open  wavy  look
    'neutral': ('dot', 0.0, 0.45, 0.0, 0.0, (0, 0)),
    'talk': ('happy', 0.1, 0.6, 0.45, 0.0, (0, 0)),
    'sad': ('dot', 0.9, -0.15, 0.0, 1.0, (0, 5)),
    'angry': ('dot', -1.0, -0.7, 0.9, 0.0, (0, 0)),
    'scared': ('wide', 1.0, -0.3, 0.35, 0.0, (0, 0)),
    'calm': ('dot', 0.15, 0.4, 0.3, 0.0, (0, 0)),
    'happy': ('happy', 0.1, 0.9, 0.0, 0.0, (0, 0)),
    'smile': ('dot', 0.1, 0.8, 0.0, 0.0, (0, 0)),
}


def face2(ctx, hc, s, mood, key, cfg, look=(0, 0)):
    eyes, brow, mouth, mopen, wavy, mlook = MOODS[mood]
    lx, ly = look[0] + mlook[0], look[1] + mlook[1]
    cx, cy = hc[0] + lx * s, hc[1] + ly * s
    lw = 5.0 * s
    girl = cfg['kind'] == 'girl'
    hair_col = cfg['hair']
    brow_col = shade(hair_col, 0.8) if hair_col.fR + hair_col.fG < 1.2 else shade(hair_col, 0.45)
    for sg in (-1, 1):
        # cheeks
        ctx.wash(ell(cx + sg * 36 * s, cy + 24 * s, 14 * s, 9 * s, 24), CHEEK, key=(key, 'ck', sg), alpha=0.5,
                 edge=0.15, amp=1.0, blend=skia.BlendMode.kSrcOver)
        e = np.array([cx + sg * 21 * s, cy + 6 * s])
        if eyes == 'dot':
            ctx.dot(e, 5.6 * s, ry=7.2 * s, key=(key, 'e', sg))
            ctx.dot(e + np.array([-1.8, -2.6]) * s, 1.7 * s, color=PAPER, key=(key, 'hl', sg))
        elif eyes == 'wide':
            ctx.loop(ell(e[0], e[1], 10 * s, 11 * s, 24), lw * 0.7, key=(key, 'ew', sg), amp=0.4)
            ctx.dot(e + np.array([0, 1.5 * s]), 4.4 * s, key=(key, 'ep', sg))
        else:
            xx = np.linspace(-8, 8, 9) * s
            ctx.line(np.stack([e[0] + xx, e[1] + 2 * s - 6 * s * (1 - (xx / (8 * s)) ** 2)], 1), lw * 0.8,
                     key=(key, 'ea', sg), taper=(0.2, 0.2), amp=0.4)
        if girl and eyes != 'wide':
            o = e + np.array([sg * 7.5 * s, -3 * s])
            ctx.line([o, o + np.array([sg * 7 * s, -5 * s])], 2.8 * s, key=(key, 'lash', sg), taper=(0.05, 0.6))
        inner = e + np.array([-sg * 8, -17 - brow * (9 if brow < 0 else 6)]) * s
        outer = e + np.array([sg * 10, -17 + brow * 3 - 2]) * s
        ctx.line([outer, (outer + inner) / 2 + np.array([0, -2.5 * s]), inner], lw * 0.85, color=brow_col,
                 key=(key, 'b', sg), taper=(0.3, 0.2), amp=0.3)
        if cfg.get('glasses'):
            ctx.loop(ell(e[0], e[1], 16 * s, 14 * s, 28), lw * 0.62, key=(key, 'gl', sg), amp=0.4)
    if cfg.get('glasses'):
        ctx.line([[cx - 5 * s, cy + 3 * s], [cx + 5 * s, cy + 3 * s]], lw * 0.55, key=(key, 'glb'), amp=0.2)
    if cfg.get('freckles'):
        r = np.random.default_rng(hseed(key, 'fr'))
        for sg in (-1, 1):
            for j in range(4):
                p = np.array([cx + sg * (30 + r.random() * 14) * s, cy + (16 + r.random() * 9) * s])
                ctx.dot(p, 1.5 * s, color=rgb('#B8744E'), alpha=0.8, key=(key, 'fk', sg, j))
    # nose
    ctx.line([[cx + 1 * s, cy + 12 * s], [cx - 3 * s, cy + 20 * s], [cx + 3 * s, cy + 22 * s]], lw * 0.6,
             color=shade(cfg['skin'], 0.55), key=(key, 'nose'), taper=(0.2, 0.3), amp=0.3)
    # mouth
    my = cy + 32 * s
    wm = (12 + 6 * max(0.0, mopen - 0.4)) * s
    xx = np.linspace(-wm, wm, 14)
    bell = 1 - (xx / wm) ** 2
    up = my + mouth * 6 * s * bell + wavy * 2.4 * s * np.sin(xx / s * 0.55)
    if mopen > 0.05:
        lo = up + mopen * 20 * s * bell ** 0.7 + 2
        m = np.vstack([np.stack([cx + xx, up], 1), np.stack([cx + xx[::-1], lo[::-1]], 1)])
        ctx.wash(m, MOUTH, key=(key, 'mf'), amp=0.5, edge=0.1, alpha=0.95)
        ctx.loop(m, lw * 0.6, key=(key, 'ml'), amp=0.3, overshoot=0.02)
    else:
        ctx.line(np.stack([cx + xx, up], 1), lw * 0.72, key=(key, 'm'), taper=(0.2, 0.2), amp=0.3)


# --------------------------------------------------------------------------
# body
# --------------------------------------------------------------------------

ARM_POSES = {
    #          elbow (dx, dy)   wrist (dx, dy)   in front of the body?
    'rest': ((10, 78), (16, 150), False),
    'open': ((30, 72), (86, 84), False),
    'point': ((58, 26), (132, 6), False),
    'fist': ((56, 50), (70, -22), False),
    'clench': ((20, 74), (30, 138), False),
    'guard': ((44, 50), (46, -26), False),
    'crossed': ((14, 78), (-58, 50), True),
    'chest': ((22, 80), (-40, 46), True),
    'shy': ((8, 80), (-30, 136), True),
    'wave': ((40, 30), (58, -50), False),
}


def hand_poly(wrist, d, s, sg, fist=False):
    """mitten hand with a thumb, pointing along d (unit); fist=True gives a clenched ball."""
    if fist:
        c = wrist + d * 18 * s
        return [ell(c[0], c[1], 16 * s, 15 * s, 28)]
    nrm = np.array([-d[1], d[0]])
    inner = nrm * sg if (nrm * sg)[0] * sg < 0 else -nrm * sg   # side facing the body
    c = wrist + d * 22 * s
    pts = ell(0, 0, 12.5 * s, 17 * s, 28)
    ang = math.atan2(d[1], d[0]) - math.pi / 2
    palm = rot(pts, ang, np.zeros(2)) + c
    tb = c - d * 6 * s + inner * 9 * s
    tdir = d * 0.8 + inner * 0.6
    thumb = chain([tb, tb + tdir * 13 * s], [6.5 * s, 5.2 * s])
    return [palm, thumb]


def person2(ctx, x, yg, s, cfg, mood, key, arms=('rest', 'rest'), lean=0.0, look=(0, 0), hands_to=(None, None),
            step=0.0, shrink=0.0):
    girl = cfg['kind'] == 'girl'
    O = np.array([x, yg], np.float64)

    def T(p):
        p = np.atleast_2d(np.asarray(p, np.float64))
        return rot(p * s + O, lean, O)

    hip_y = -165
    sh_y = -312 + shrink * 6
    head_c = np.array([0.0, sh_y - 96 + shrink * 16])
    SW = 56 if girl else 64       # shoulder joint x
    skin, top = cfg['skin'], cfg['top']
    sleeve_col = top if cfg['top_style'] != 'vest' else top

    # ---------- hair behind everything
    hs = cfg['hair_style']
    if girl and hs == 'long':
        th = np.linspace(0, 2 * np.pi, 140, endpoint=False)
        rr = 1 + 0.05 * np.sin(th * 11)
        back = np.stack([head_c[0] + 84 * rr * np.cos(th),
                         head_c[1] + 40 + 128 * rr * np.sin(th) * np.where(np.sin(th) > 0, 1.0, 0.62)], 1)
        shape(ctx, [T(back)], cfg['hair'], (key, 'hairback'), width=4.4 * s)
    elif girl and hs == 'curly':
        rng = np.random.default_rng(7)
        blobs = [ell(head_c[0], head_c[1] + 6, 98, 96, 60)]
        for j in range(16):
            a = j / 16 * 2 * np.pi
            blobs.append(ell(head_c[0] + 92 * math.cos(a), head_c[1] + 6 + 90 * math.sin(a) * (0.9 if math.sin(a) < 0 else 0.75),
                             26 + rng.random() * 8, 26 + rng.random() * 8, 20))
        shape(ctx, [T(b) for b in blobs], cfg['hair'], (key, 'hairback'), width=4.4 * s)
    elif girl and hs == 'bob':
        bob = spline([[-70, -30], [-60, -70], [0, -84], [60, -70], [70, -30], [76, 30], [66, 52], [40, 46], [-40, 46],
                      [-66, 52], [-76, 30]])
        shape(ctx, [T(bob + head_c)], cfg['hair'], (key, 'hairback'), width=4.4 * s)

    # ---------- legs / pants
    legs = []
    ankles = []
    r_leg = [24, 21, 18] if girl else [27, 24, 21]
    for sg in (-1, 1):
        top_p = np.array([sg * 30, hip_y + 12])
        ank = np.array([sg * 34 + (step * 36 if sg > 0 else 0), -26])
        knee = (top_p + ank) / 2 + np.array([sg * 3, 0])
        legs.append(chain([top_p, knee, ank], r_leg))
        ankles.append(ank)
    pelvis = spline([[-62, hip_y - 20], [62, hip_y - 20], [60, hip_y + 34], [0, hip_y + 44], [-60, hip_y + 34]])
    shape(ctx, [T(p) for p in legs + [pelvis]], cfg['pants'], (key, 'pants'), width=4.5 * s)
    ctx.line(T([[0, hip_y + 28], [0, hip_y + 62]]), 3.2 * s, key=(key, 'crotch'), alpha=0.6)
    for i, sg in enumerate((-1, 1)):
        ank = ankles[i]
        if cfg.get('cuffs'):
            shape(ctx, [T(chain([ank + np.array([-r_leg[2] - 3, -4]), ank + np.array([r_leg[2] + 3, -4])], [8]))],
                  shade(cfg['pants'], 0.92), (key, 'cuff', sg), width=4 * s)
        if cfg['shoe_style'] == 'boot':
            boot = spline([[ank[0] - 20, -44], [ank[0] + 20, -44], [ank[0] + 24 + sg * 8, -12], [ank[0] + sg * 14 + 26, 0],
                           [ank[0] + sg * 14 - 26, 0], [ank[0] - 24 + sg * 8, -12]])
            shape(ctx, [T(boot)], cfg['shoes'], (key, 'shoe', sg), width=4.2 * s)
        else:
            shoe = ell(ank[0] + sg * 8, -14, 30, 15, 36)
            shape(ctx, [T(shoe)], cfg['shoes'], (key, 'shoe', sg), width=4.2 * s)
            sole = chain([[ank[0] + sg * 8 - 27, -4], [ank[0] + sg * 8 + 27, -4]], [4.5])
            shape(ctx, [T(sole)], rgb('#F2EFE6'), (key, 'sole', sg), width=3.4 * s, edge=0.1)

    # ---------- arms geometry
    arm_parts, front_arms, hands_back, hands_front, fists = [], [], [], [], []
    for i, sg in enumerate((-1, 1)):
        J = np.array([sg * SW, sh_y + 30])
        spec = arms[i]
        if hands_to[i] is not None:
            wrist_w = np.asarray(hands_to[i], np.float64)
            wrist = rot(np.atleast_2d(wrist_w), -lean, O)[0]
            wrist = (wrist - O) / s
            elbow = (J + wrist) / 2 + np.array([sg * 16, 26])
            front = False
        else:
            e_off, w_off, front = ARM_POSES[spec]
            elbow = J + np.array([sg * e_off[0], e_off[1]])
            wrist = J + np.array([sg * w_off[0], w_off[1]])
        rad = [18, 16, 14] if girl else [21, 18, 16]
        sleeve = chain([J, elbow, wrist], rad)
        d = wrist - elbow
        d = d / (np.hypot(*d) + 1e-9)
        hp = hand_poly(wrist, d, 1.0, sg, fist=(spec in ('clench', 'fist') and hands_to[i] is None))
        if spec in ('clench', 'fist') and hands_to[i] is None:
            fists.append((wrist + d * 18, d))
        if front:
            front_arms.append((sleeve, hp, sg))
        else:
            arm_parts.append(sleeve)
            hands_back.append((hp, sg))

    # hands that hang outside the body go under the sleeves
    for hp, sg in hands_back:
        shape(ctx, [T(p) for p in hp], skin, (key, 'hand', sg), width=4.2 * s)
    for j, (fc, d) in enumerate(fists):  # knuckle creases
        nrm = np.array([-d[1], d[0]])
        for k in (-1, 0, 1):
            p0 = fc + d * 6 + nrm * k * 7
            ctx.line(T([p0, p0 + d * 7]), 2.6 * s, key=(key, 'kn', j, k), alpha=0.7)

    # ---------- neck (under the collar)
    neck = chain([[0, sh_y + 12], [0, head_c[1] + 30]], [14 if girl else 16])
    if cfg['top_style'] != 'hoodie':
        shape(ctx, [T(neck)], skin, (key, 'neck'), width=4.4 * s)

    # ---------- torso
    if girl:
        tp = [[-20, sh_y - 2], [-48, sh_y + 2], [-66, sh_y + 18], [-68, sh_y + 54], [-56, hip_y - 40], [-66, hip_y + 18],
              [0, hip_y + 24], [66, hip_y + 18], [56, hip_y - 40], [68, sh_y + 54], [66, sh_y + 18], [48, sh_y + 2],
              [20, sh_y - 2], [0, sh_y + 16]]
    else:
        tp = [[-24, sh_y - 4], [-56, sh_y], [-76, sh_y + 18], [-80, sh_y + 56], [-74, hip_y - 10], [-72, hip_y + 24],
              [0, hip_y + 28], [72, hip_y + 24], [74, hip_y - 10], [80, sh_y + 56], [76, sh_y + 18], [56, sh_y],
              [24, sh_y - 4], [0, sh_y + 10]]
    torso = spline(tp)
    body_col = cfg['top'] if cfg['top_style'] not in ('vest', 'cardigan') else (
        cfg['top'] if cfg['top_style'] == 'vest' else cfg['top'])
    torso_col = cfg['top'] if cfg['top_style'] != 'cardigan' else cfg['top']
    shape(ctx, [T(torso)] + [T(a) for a in arm_parts], torso_col, (key, 'torso'), width=4.6 * s)
    # soft shadow down one side for volume
    shadow = spline([[40, sh_y + 40], [70, sh_y + 60], [66, hip_y + 10], [44, hip_y + 18], [50, hip_y - 60]])
    ctx.wash(T(shadow), shade(torso_col, 0.8), key=(key, 'shd'), alpha=0.35, edge=0.0, amp=2)

    st = cfg['top_style']
    if st == 'hoodie':
        hood = spline([[-50, sh_y + 6], [-46, sh_y - 14], [0, sh_y - 22], [46, sh_y - 14], [50, sh_y + 6], [0, sh_y + 20]])
        shape(ctx, [T(hood)], shade(top, 0.93), (key, 'hood'), width=4.2 * s)
        shape(ctx, [T(neck)], skin, (key, 'neck'), width=4.4 * s)
        pocket = [[-42, hip_y - 6], [-34, hip_y - 58], [34, hip_y - 58], [42, hip_y - 6]]
        ctx.line(T(pocket), 3.4 * s, key=(key, 'pocket'), alpha=0.7, taper=(0.05, 0.05))
        for sg in (-1, 1):
            ctx.line(T([[sg * 12, sh_y + 14], [sg * 14, sh_y + 44], [sg * 13, sh_y + 66]]), 3.0 * s,
                     key=(key, 'cord', sg), alpha=0.85)
        ctx.line(T([[-70, hip_y + 8], [70, hip_y + 8]]), 3 * s, key=(key, 'hem'), alpha=0.55)
    elif st == 'sweater':
        ctx.line(T(spline([[-26, sh_y - 1], [0, sh_y + 16], [26, sh_y - 1]], closed=False)), 3.4 * s, key=(key, 'col'),
                 alpha=0.7)
        for j in range(9):
            xx = -60 + j * 15
            ctx.line(T([[xx, hip_y + 8], [xx, hip_y + 22]]), 2.6 * s, key=(key, 'rib', j), alpha=0.5)
    elif st == 'vest':
        for sg in (-1, 1):
            vp = spline([[sg * 22, sh_y + 8], [sg * 58, sh_y + 10], [sg * 66, sh_y + 50], [sg * 56, hip_y - 40],
                         [sg * 66, hip_y + 18], [sg * 14, hip_y + 16], [sg * 16, sh_y + 60]])
            shape(ctx, [T(vp)], cfg['vest'], (key, 'vest', sg), width=4.6 * s)
            collar = [[sg * 4, sh_y + 14], [sg * 22, sh_y - 2], [sg * 20, sh_y + 20]]
            shape(ctx, [T(np.array(collar, np.float64))], cfg['top'], (key, 'collar', sg), width=3.6 * s, amp=0.5)
        for j in range(3):
            ctx.dot(T([[0, sh_y + 44 + j * 34]])[0], 3.2 * s, key=(key, 'btn', j), alpha=0.8)
    elif st == 'cardigan':
        q = np.array([[-22, sh_y], [22, sh_y], [12, sh_y + 60], [14, hip_y + 20], [-14, hip_y + 20], [-12, sh_y + 60]],
                     np.float64)
        inner = np.vstack([np.linspace(q[i], q[(i + 1) % len(q)], 8, endpoint=False) for i in range(len(q))])
        shape(ctx, [T(inner)], cfg['inner'], (key, 'inner'), width=4 * s)
        for j in range(3):
            ctx.dot(T([[-22, sh_y + 50 + j * 32]])[0], 3.4 * s, key=(key, 'btn', j), alpha=0.8)

    # ---------- arms in front of the body
    for sleeve, hp, sg in front_arms:
        shape(ctx, [T(p) for p in hp], skin, (key, 'handf', sg), width=4.2 * s)
        shape(ctx, [T(sleeve)], torso_col, (key, 'armf', sg), width=4.4 * s)

    # ---------- head
    hc = head_c
    if not girl or hs in ('curly', 'bob'):
        for sg in (-1, 1):
            if girl and hs == 'bob':
                continue
            shape(ctx, [T(ell(hc[0] + sg * 53, hc[1] + 10, 11, 15, 20))], skin, (key, 'ear', sg), width=4 * s)
            if cfg.get('earrings'):
                ctx.loop(T(ell(hc[0] + sg * 54, hc[1] + 32, 7, 8, 20)), 3.2 * s, color=cfg['earrings'],
                         key=(key, 'ring', sg), amp=0.3)
    head = spline([[-50, -20], [-40, -52], [0, -60], [40, -52], [50, -20], [48, 16], [30, 50], [0, 60], [-30, 50], [-48, 16]])
    shape(ctx, [T(head + hc)], skin, (key, 'head'), width=4.6 * s)
    ctx.wash(T(ell(hc[0], hc[1] + 66, 24, 7, 24)), shade(skin, 0.75), key=(key, 'chin'), alpha=0.35, edge=0, amp=0.5)

    # ---------- hair in front
    hair = cfg['hair']
    if not girl and hs == 'messy':
        cap = spline([[-56, 0], [-54, -44], [-20, -70], [26, -68], [56, -40], [58, -2], [44, -16], [36, -30],
                      [20, -20], [8, -34], [-10, -22], [-24, -34], [-40, -18]])
        shape(ctx, [T(cap + hc)], hair, (key, 'hair'), width=4.4 * s)
        for j in range(4):
            ctx.line(T(np.array([[-30 + j * 18, -58], [-24 + j * 18, -40]], np.float64) + hc), 2.8 * s,
                     color=shade(hair, 1.6), alpha=0.5, key=(key, 'hs', j))
        ctx.line(T(np.array([[6, -66], [12, -84], [22, -78]], np.float64) + hc), 4 * s, key=(key, 'tuft'))
    elif not girl and hs == 'curly':
        blobs = [spline([[-54, -8], [-54, -46], [0, -70], [54, -46], [54, -8], [30, -34], [-30, -34]])]
        for j in range(9):
            a = math.pi + j / 8 * math.pi
            blobs.append(ell(hc[0] * 0 + 52 * math.cos(a), -22 + 46 * math.sin(a), 17, 16, 18))
        shape(ctx, [T(b + hc) for b in blobs], hair, (key, 'hair'), width=4.4 * s)
        for j in range(5):
            c0 = np.array([-34 + j * 17, -52 + (j % 2) * 10], np.float64)
            u = np.linspace(0, 5.5, 12)
            ctx.line(T(c0 + np.stack([np.cos(u) * 5, np.sin(u) * 5], 1) + hc), 2.6 * s, color=shade(hair, 2.2),
                     alpha=0.5, key=(key, 'cl', j))
    elif not girl and hs == 'side':
        cap = spline([[-56, -4], [-52, -46], [-10, -70], [36, -64], [58, -36], [58, -6], [46, -26], [10, -40],
                      [-22, -34], [-44, -18]])
        shape(ctx, [T(cap + hc)], hair, (key, 'hair'), width=4.4 * s)
        ctx.line(T(np.array([[-18, -66], [-4, -46], [30, -36]], np.float64) + hc), 3 * s, color=shade(hair, 1.5),
                 alpha=0.6, key=(key, 'part'))
    elif girl and hs == 'long':
        bang = spline([[-58, 10], [-56, -40], [-14, -66], [30, -62], [58, -34], [60, 12], [46, -18], [24, -34], [2, -48],
                       [-16, -30], [-40, -16]])
        shape(ctx, [T(bang + hc)], hair, (key, 'bang'), width=4.4 * s)
        for sg in (-1, 1):
            lock = spline([[sg * 50, -10], [sg * 62, 40], [sg * 58, 90], [sg * 70, 140], [sg * 60, 180], [sg * 44, 150],
                           [sg * 44, 90], [sg * 40, 40], [sg * 38, 0]])
            shape(ctx, [T(lock + hc)], hair, (key, 'lock', sg), width=4.6 * s)
            ctx.line(T(np.array([[sg * 52, 30], [sg * 56, 80], [sg * 54, 130]], np.float64) + hc), 2.6 * s,
                     color=shade(hair, 0.7), alpha=0.6, key=(key, 'lk', sg))
    elif girl and hs == 'curly':
        for j in range(6):
            a = math.pi * 1.1 + j / 5 * math.pi * 0.8
            c0 = np.array([48 * math.cos(a), -34 + 34 * math.sin(a)])
            shape(ctx, [T(ell(c0[0] + hc[0], c0[1] + hc[1], 18, 16, 18))], hair, (key, 'fc', j), width=4.4 * s)
    elif girl and hs == 'bob':
        fringe = spline([[-58, 6], [-56, -40], [0, -66], [56, -40], [58, 6], [48, -20], [20, -30], [-10, -24],
                         [-40, -28], [-50, -10]])
        shape(ctx, [T(fringe + hc)], hair, (key, 'fringe'), width=4.4 * s)
        clip = chain([[28, -34], [46, -42]], [5])
        shape(ctx, [T(clip + hc)], rgb('#6FA5A0'), (key, 'clip'), width=3 * s)

    face2(ctx, T(hc)[0], s, mood, (key, 'face'), cfg, look=look)
    return T(hc)[0]

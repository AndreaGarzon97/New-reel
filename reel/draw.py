"""Hand-drawn look primitives: wobbly brush strokes, watercolor washes,
paper/crayon textures and hand-lettered text, all on top of skia."""
import math
import zlib
from functools import lru_cache

import numpy as np
import skia
from PIL import Image

W, H = 1080, 1920
FONTS = __file__.rsplit('/', 2)[0] + '/fonts/'


def hseed(*keys):
    return zlib.crc32(repr(keys).encode()) & 0xFFFFFFFF


def rgb(h, a=1.0):
    h = h.lstrip('#')
    return skia.Color4f(int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)


def mix(c1, c2, t):
    return skia.Color4f(c1.fR + (c2.fR - c1.fR) * t, c1.fG + (c2.fG - c1.fG) * t,
                        c1.fB + (c2.fB - c1.fB) * t, c1.fA + (c2.fA - c1.fA) * t)


def shade(c, k):
    return skia.Color4f(c.fR * k, c.fG * k, c.fB * k, c.fA)


def with_alpha(c, a):
    return skia.Color4f(c.fR, c.fG, c.fB, a)


# --------------------------------------------------------------------------
# noise textures
# --------------------------------------------------------------------------

def fbm(h, w, octaves, seed):
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    tot = 0
    for cells, amp in octaves:
        ch = max(2, int(round(cells * h / max(h, w))))
        cw = max(2, int(round(cells * w / max(h, w))))
        small = rng.random((ch, cw)).astype(np.float32)
        img = Image.fromarray(small, mode='F').resize((w, h), Image.BICUBIC)
        out += amp * np.asarray(img)
        tot += amp
    out /= tot
    lo, hi = np.percentile(out, 1), np.percentile(out, 99)
    return np.clip((out - lo) / (hi - lo), 0, 1)


def streaks(h, w, seed, sx=90, sy=3, angle=0.0):
    """crayon-ish directional noise: stretched along x (rotated without empty corners)."""
    rng = np.random.default_rng(seed)
    d = int(math.ceil(math.hypot(h, w))) if angle else max(h, w)
    hh, ww = (d, d) if angle else (h, w)
    small = rng.random((max(2, hh // sy), max(2, ww // sx))).astype(np.float32)
    img = Image.fromarray(small, mode='F').resize((ww, hh), Image.BICUBIC)
    if angle:
        img = img.rotate(angle, resample=Image.BICUBIC, expand=False)
        top, left = (hh - h) // 2, (ww - w) // 2
        img = img.crop((left, top, left + w, top + h))
    return np.asarray(img)


def fine_grain(h, w, seed, sigma=0.8):
    rng = np.random.default_rng(seed)
    g = rng.random((h, w)).astype(np.float32)
    from scipy.ndimage import gaussian_filter
    g = gaussian_filter(g, sigma)
    lo, hi = np.percentile(g, 1), np.percentile(g, 99)
    return np.clip((g - lo) / (hi - lo), 0, 1)


def alpha_image(a):
    """numpy float alpha (h,w) -> skia image usable as alpha texture."""
    a8 = np.ascontiguousarray(np.clip(a * 255, 0, 255).astype(np.uint8))
    return skia.Image.fromarray(a8, colorType=skia.kAlpha_8_ColorType)


def rgb_image(rgbf):
    h, w, _ = rgbf.shape
    arr = np.empty((h, w, 4), np.uint8)
    arr[..., :3] = np.clip(rgbf * 255, 0, 255).astype(np.uint8)
    arr[..., 3] = 255
    return skia.Image.fromarray(arr)


NTEX = 3


@lru_cache(None)
def ink_grain(i):
    """crayon/pencil grain for line work: mostly solid with paper-tooth dropouts."""
    g = fine_grain(H, W, 100 + i, 0.6)
    s = streaks(H, W, 200 + i, 40, 2, angle=25)
    v = 0.55 * g + 0.45 * s
    a = np.clip(0.30 + 1.25 * v, 0, 1)
    a = 0.25 + 0.75 * a ** 0.8
    return alpha_image(a)


@lru_cache(None)
def pigment(i):
    """watercolor pigment density: blotches + granulation."""
    b = fbm(H, W, [(6, 1.0), (14, 0.7), (40, 0.35)], 300 + i)
    g = fine_grain(H, W, 400 + i, 1.2)
    a = 0.62 + 0.30 * b + 0.12 * (g - 0.5)
    return alpha_image(np.clip(a, 0, 1))


@lru_cache(None)
def pastel(i):
    """dry pastel / colored pencil fill: streaky, lets paper through."""
    s = streaks(H, W, 500 + i, 70, 3, angle=-18)
    g = fine_grain(H, W, 600 + i, 0.7)
    a = np.clip(0.35 + 0.55 * s + 0.35 * (g - 0.5), 0, 1)
    return alpha_image(a)


@lru_cache(None)
def paper_rgb(seed=7, base='#F1E8D6'):
    c = np.array([int(base[1:3], 16), int(base[3:5], 16), int(base[5:7], 16)], np.float32) / 255
    mott = fbm(H, W, [(5, 1.0), (16, 0.5), (60, 0.25)], seed)
    g = fine_grain(H, W, seed + 1, 0.9)
    fib = streaks(H, W, seed + 2, 120, 2, angle=35)
    k = 0.965 + 0.05 * mott + 0.035 * (g - 0.5) + 0.02 * (fib - 0.5)
    img = c[None, None, :] * k[..., None]
    # soft vignette like a scanned sheet
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = ((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.75)) ** 2
    img *= (1 - 0.10 * np.clip(d, 0, 1.5))[..., None]
    return np.clip(img, 0, 1)


@lru_cache(None)
def film_grain(i):
    g = fine_grain(H, W, 900 + i, 0.5)
    arr = np.empty((H, W, 4), np.uint8)
    v = (128 + (g - 0.5) * 60).astype(np.uint8)
    arr[..., 0] = v
    arr[..., 1] = v
    arr[..., 2] = v
    arr[..., 3] = 255
    return skia.Image.fromarray(arr)


_shader_cache = {}


def tex_shader(kind, i):
    key = (kind, i)
    if key not in _shader_cache:
        img = {'ink': ink_grain, 'pig': pigment, 'pastel': pastel}[kind](i % NTEX)
        _shader_cache[key] = img.makeShader(skia.TileMode.kRepeat, skia.TileMode.kRepeat)
    return _shader_cache[key]


_paint_cache = {}


def textured_paint(color, kind, i, blend=None, style=None):
    # skia-python's setShader is very slow with big images, so paints are
    # built once per texture/blend combination and only re-coloured.
    key = (kind, i % NTEX, blend, style)
    p = _paint_cache.get(key)
    if p is None:
        p = skia.Paint(AntiAlias=True)
        p.setShader(tex_shader(kind, i % NTEX))
        if blend is not None:
            p.setBlendMode(blend)
        if style is not None:
            p.setStyle(style)
        _paint_cache[key] = p
    # alpha-only image shader: skia tints it with the paint colour
    p.setColor4f(color)
    return p


# --------------------------------------------------------------------------
# wobble
# --------------------------------------------------------------------------

class Wob:
    """smooth 1D noise made of a few random sines (periodic on [0,1])."""

    def __init__(self, seed, n=5):
        r = np.random.default_rng(seed)
        self.ph = r.random(n) * 2 * np.pi
        self.am = (r.random(n) * 0.7 + 0.3) / np.arange(1, n + 1) ** 0.9
        self.am /= self.am.sum() * 0.6

    def __call__(self, u, freq=1.0):
        k = np.arange(1, len(self.ph) + 1)
        return (self.am[None, :] * np.sin(2 * np.pi * freq * k[None, :] * np.asarray(u)[:, None]
                                           + self.ph[None, :])).sum(1)


def arclen(pts):
    seg = np.hypot(*np.diff(pts, axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    return s


def resample(pts, step=3.5):
    s = arclen(pts)
    L = s[-1]
    if L < 1e-3:
        return pts
    n = max(4, int(L / step))
    u = np.linspace(0, L, n)
    return np.stack([np.interp(u, s, pts[:, 0]), np.interp(u, s, pts[:, 1])], 1)


def normals(pts):
    d = np.gradient(pts, axis=0)
    n = np.hypot(d[:, 0], d[:, 1]) + 1e-9
    return np.stack([-d[:, 1] / n, d[:, 0] / n], 1)


def wobble(pts, key, boil, amp=2.0, freq=1.6, drift=1.2):
    """displace along normals with boil-dependent smooth noise."""
    pts = resample(np.asarray(pts, np.float64))
    s = arclen(pts)
    L = max(s[-1], 1)
    u = s / L
    f = freq * max(1.0, L / 300) ** 0.6
    w1 = Wob(hseed(key, 'w', boil))
    nrm = normals(pts)
    off = amp * w1(u, f)
    r = np.random.default_rng(hseed(key, 'd', boil))
    dx, dy = (r.random(2) - 0.5) * 2 * drift
    return pts + nrm * off[:, None] + np.array([dx, dy])


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a + 1e-9), 0, 1)
    return t * t * (3 - 2 * t)


def brush_path(pts, width, key=0, taper=(0.18, 0.25), min_w=0.35, press=0.22, upto=1.0):
    """variable-width stroke outline as a filled skia.Path."""
    pts = np.asarray(pts, np.float64)
    if len(pts) < 2:
        return skia.Path()
    s = arclen(pts)
    L = max(s[-1], 1e-3)
    u = s / L
    if upto < 1.0:
        m = u <= upto
        if m.sum() < 2:
            return skia.Path()
        # add interpolated end point
        k = m.sum()
        if k < len(pts):
            t = (upto * L - s[k - 1]) / max(s[k] - s[k - 1], 1e-6)
            end = pts[k - 1] + (pts[k] - pts[k - 1]) * t
            pts = np.vstack([pts[:k], end])
        else:
            pts = pts[:k]
        s = arclen(pts)
        u = s / L
    ta, tb = taper
    wf = np.ones(len(pts))
    if ta > 0:
        wf *= min_w + (1 - min_w) * smoothstep(0, ta, u)
    if tb > 0:
        wf *= min_w + (1 - min_w) * smoothstep(0, tb, 1 - u)
    wp = Wob(hseed(key, 'p'))
    wf *= 1 + press * wp(u, 1.3 * max(1, L / 250))
    w = width * wf / 2
    nrm = normals(pts)
    left = pts + nrm * w[:, None]
    right = pts - nrm * w[:, None]
    path = skia.Path()
    path.moveTo(*left[0])
    for p in left[1:]:
        path.lineTo(*p)
    # end cap
    c = pts[-1]
    a0 = math.atan2(nrm[-1, 1], nrm[-1, 0])
    for j in range(1, 6):
        a = a0 - math.pi * j / 6
        path.lineTo(c[0] + w[-1] * math.cos(a), c[1] + w[-1] * math.sin(a))
    for p in right[::-1]:
        path.lineTo(*p)
    c = pts[0]
    a0 = math.atan2(-nrm[0, 1], -nrm[0, 0])
    for j in range(1, 6):
        a = a0 - math.pi * j / 6
        path.lineTo(c[0] + w[0] * math.cos(a), c[1] + w[0] * math.sin(a))
    path.close()
    return path


def poly_path(pts, close=True):
    p = skia.Path()
    pts = np.asarray(pts)
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    if close:
        p.close()
    return p


# --------------------------------------------------------------------------
# drawing context
# --------------------------------------------------------------------------

INK = rgb('#2E2724')
PAPER = rgb('#F3EBDC')


class Ctx:
    def __init__(self, canvas, boil, t=0.0):
        self.cv = canvas
        self.boil = boil
        self.t = t

    # ---- line work
    def line(self, pts, width=6.0, color=INK, key=0, amp=1.6, taper=(0.18, 0.25),
             min_w=0.35, upto=1.0, wob=True, alpha=1.0, freq=1.6):
        pts = np.asarray(pts, np.float64)
        if wob:
            pts = wobble(pts, key, self.boil, amp=amp, freq=freq)
        else:
            pts = resample(pts)
        path = brush_path(pts, width, key=(key, self.boil // 3), taper=taper, min_w=min_w, upto=upto)
        col = with_alpha(color, color.fA * alpha)
        self.cv.drawPath(path, textured_paint(col, 'ink', self.boil))
        return pts

    def loop(self, pts, width=6.0, color=INK, key=0, amp=1.6, overshoot=0.08, upto=1.0, alpha=1.0,
             start=None):
        """closed shape drawn as one stroke that overshoots its start a little."""
        pts = np.asarray(pts, np.float64)
        n = len(pts)
        r = np.random.default_rng(hseed(key, 'start'))
        st = int((r.random() if start is None else start) * n) % n
        extra = int(overshoot * n)
        idx = [(st + i) % n for i in range(n + extra)]
        q = pts[idx].copy()
        # the overshoot drifts slightly outwards, as a real pen would
        if extra:
            ctr = pts.mean(0)
            d = q[-extra:] - ctr
            q[-extra:] += d * np.linspace(0, 0.045, extra)[:, None]
        return self.line(q, width, color, key, amp, taper=(0.06, 0.1), min_w=0.3, upto=upto, alpha=alpha)

    # ---- fills
    def wash(self, pts, color, key=0, amp=4.0, offset=(0, 0), edge=0.55, alpha=1.0, kind='pig',
             blend=skia.BlendMode.kMultiply, edge_w=16):
        pts = np.asarray(pts, np.float64)
        r = np.random.default_rng(hseed(key, 'mis'))
        mis = (r.random(2) - 0.5) * 2 * np.array([5, 4]) + np.array(offset)
        q = wobble(pts, (key, 'fill'), self.boil // 2, amp=amp, freq=1.2, drift=1.0) + mis
        path = poly_path(q)
        col = with_alpha(color, color.fA * alpha)
        self.cv.drawPath(path, textured_paint(col, kind, self.boil // 2 + hseed(key) % 3, blend=blend))
        if edge > 0:
            self.cv.save()
            self.cv.clipPath(path, doAntiAlias=True)
            pe = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=edge_w)
            pe.setColor4f(with_alpha(shade(color, 0.82), edge * alpha))
            pe.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, edge_w * 0.3))
            pe.setBlendMode(blend)
            self.cv.drawPath(path, pe)
            pe2 = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=3.5)
            pe2.setColor4f(with_alpha(shade(color, 0.7), 0.35 * alpha))
            pe2.setBlendMode(blend)
            self.cv.drawPath(path, pe2)
            self.cv.restore()
        return q

    def under(self, pts, key=0):
        """opaque paper underlay so washes read as solid objects over busy backgrounds."""
        return self.solid(pts, PAPER, key=(key, 'under'), amp=0.8)

    def solid(self, pts, color, key=0, amp=2.0, alpha=1.0, kind='pig'):
        """opaque-ish light fill (paper-white speech bubbles etc)."""
        q = wobble(np.asarray(pts, np.float64), (key, 'solid'), self.boil // 2, amp=amp, freq=1.2)
        p = skia.Paint(AntiAlias=True)
        p.setColor4f(with_alpha(color, alpha))
        self.cv.drawPath(poly_path(q), p)
        return q

    def dot(self, c, r, color=INK, key=0, alpha=1.0, ry=None):
        th = np.linspace(0, 2 * np.pi, 24, endpoint=False)
        ry = r if ry is None else ry
        pts = np.stack([c[0] + r * np.cos(th), c[1] + ry * np.sin(th)], 1)
        q = wobble(pts, (key, 'dot'), self.boil, amp=0.6, freq=1.0, drift=0.6)
        self.cv.drawPath(poly_path(q), textured_paint(with_alpha(color, alpha), 'ink', self.boil))


# --------------------------------------------------------------------------
# lettering
# --------------------------------------------------------------------------

_tf = {}


def font(name, size):
    if name not in _tf:
        _tf[name] = skia.Typeface.MakeFromFile(FONTS + name)
    f = skia.Font(_tf[name], size)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    f.setSubpixel(True)
    return f


def _glyph_layout(segs, fnt, spacing):
    items = []
    x = 0.0
    for text, col in segs:
        for ch in text:
            w = fnt.measureText(ch) * spacing
            items.append((ch, col, x, w))
            x += w
    return items, x


def text_width(segs, fnt, spacing=1.0):
    if isinstance(segs, str):
        segs = [(segs, INK)]
    return _glyph_layout(segs, fnt, spacing)[1]


def lettering(ctx, segs, x, y, fnt, key, reveal=1e9, align='center', spacing=1.0,
              rot=2.2, bounce=3.0, shake=0.0, alpha=1.0, color=INK, boil_amt=1.0, weight=0.0):
    """hand-lettered line: every glyph slightly rotated/offset, 'written' left to right.
    reveal = number of glyphs visible (float)."""
    if isinstance(segs, str):
        segs = [(segs, color)]
    items, total = _glyph_layout(segs, fnt, spacing)
    x0 = x - total / 2 if align == 'center' else (x - total if align == 'right' else x)
    cv = ctx.cv
    size = fnt.getSize()
    n_drawn = 0
    for i, (ch, col, gx, gw) in enumerate(items):
        vis = reveal - i
        if vis <= 0:
            break
        if ch == ' ':
            continue
        r = np.random.default_rng(hseed(key, i))
        a, dy, sc = (r.random() - 0.5) * 2 * rot, (r.random() - 0.5) * 2 * bounce, 1 + (r.random() - 0.5) * 0.07
        rb = np.random.default_rng(hseed(key, i, ctx.boil))
        a += (rb.random() - 0.5) * 1.4 * boil_amt
        bx, by = (rb.random(2) - 0.5) * 1.6 * boil_amt
        if shake:
            rs = np.random.default_rng(hseed(key, i, 'shake', int(ctx.t * 15)))
            bx += (rs.random() - 0.5) * 2 * shake
            by += (rs.random() - 0.5) * 2 * shake
        cv.save()
        cv.translate(x0 + gx + gw / 2 + bx, y + dy + by)
        cv.rotate(a)
        cv.scale(sc, sc)
        if vis < 1:
            cv.clipRect(skia.Rect.MakeLTRB(-gw / 2 - 4, -size * 1.3, -gw / 2 + gw * vis + 2, size * 0.6))
        if weight > 0:
            p = textured_paint(with_alpha(col, col.fA * alpha), 'ink', ctx.boil,
                               style=skia.Paint.kStrokeAndFill_Style)
            p.setStrokeWidth(weight)
            p.setStrokeJoin(skia.Paint.kRound_Join)
        else:
            p = textured_paint(with_alpha(col, col.fA * alpha), 'ink', ctx.boil)
        cv.drawString(ch, -gw / 2 / spacing, 0, fnt, p)
        cv.restore()
        n_drawn += 1
    return x0, total


def glyph_count(segs):
    if isinstance(segs, str):
        return len(segs)
    return sum(len(t) for t, _ in segs)

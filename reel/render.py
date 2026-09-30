"""Renders the reel: python3 render.py [--sheet t1,t2,...] [--out file]"""
import math
import os
import subprocess
import sys
from functools import lru_cache

import numpy as np
import skia

from draw import H, W, Ctx, fbm, film_grain
from scenes import BOUNDS, SCENES, signature

FPS_DRAW = 15          # drawn "on twos"
FPS_OUT = 30
DUR = 60.0
WIPE = 0.4


@lru_cache(None)
def wipe_noise():
    return fbm(H, W, [(5, 1.0), (18, 0.5), (60, 0.2)], 4242)


def render_scene(k, t, boil):
    surf = skia.Surface(W, H)
    cv = surf.getCanvas()
    ctx = Ctx(cv, boil, t)
    SCENES[k](ctx, t - BOUNDS[k])
    signature(ctx)
    # analog grain, changes with the drawings
    p = skia.Paint()
    p.setBlendMode(skia.BlendMode.kOverlay)
    p.setAlphaf(0.45)
    cv.drawImage(film_grain(boil % 3), 0, 0, skia.SamplingOptions(), p)
    return surf.makeImageSnapshot().toarray()


def render_time(t, boil=None):
    if boil is None:
        boil = int(t * FPS_DRAW) // 2
    k = max(i for i in range(len(SCENES)) if BOUNDS[i] <= t) if t < DUR else len(SCENES) - 1
    # wipe into the next scene
    for j in range(1, len(SCENES)):
        b = BOUNDS[j]
        if b - WIPE / 2 <= t < b + WIPE / 2:
            p = (t - (b - WIPE / 2)) / WIPE
            A = render_scene(j - 1, t, boil).astype(np.float32)
            B = render_scene(j, t, boil).astype(np.float32)
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            v = xx + 0.28 * (H - yy) + 260 * wipe_noise()
            edge = -300 + p * (W + 0.28 * H + 700)
            m = np.clip((edge - v) / 50 + 0.5, 0, 1)[..., None]
            return (A * (1 - m) + B * m).astype(np.uint8)
    return render_scene(k, t, boil)


def frame(i):
    return render_time(i / FPS_DRAW, i // 2)


def main():
    args = sys.argv[1:]
    if args and args[0] == '--sheet':
        from PIL import Image
        ts = [float(x) for x in args[1].split(',')]
        out = args[2] if len(args) > 2 else 'sheet.png'
        ims = [Image.fromarray(render_time(t)[..., [2, 1, 0]]).resize((540, 960), Image.LANCZOS) for t in ts]
        cols = min(4, len(ims))
        rows = math.ceil(len(ims) / cols)
        sheet = Image.new('RGB', (540 * cols, 960 * rows), 'white')
        for n, im in enumerate(ims):
            sheet.paste(im, ((n % cols) * 540, (n // cols) * 960))
        sheet.save(out)
        return
    if args and args[0] == '--still':
        from PIL import Image
        Image.fromarray(render_time(float(args[1]))[..., [2, 1, 0]]).save(args[2])
        return
    out = args[args.index('--out') + 1] if '--out' in args else 'video_noaudio.mp4'
    n = int(DUR * FPS_DRAW)
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', f'{W}x{H}',
           '-r', str(FPS_DRAW), '-i', '-', '-vf', f'fps={FPS_OUT}', '-c:v', 'libx264', '-preset', 'slow',
           '-crf', '18', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-movflags', '+faststart', out]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    from multiprocessing import Pool
    with Pool(int(os.environ.get('JOBS', os.cpu_count()))) as pool:
        for i, fr in enumerate(pool.imap(frame, range(n), chunksize=4)):
            enc.stdin.write(np.ascontiguousarray(fr).tobytes())
            if i % 30 == 0:
                print(f'frame {i}/{n}', flush=True)
    enc.stdin.close()
    enc.wait()


if __name__ == '__main__':
    main()

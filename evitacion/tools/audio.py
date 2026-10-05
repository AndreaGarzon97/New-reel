"""Música original + diseño sonoro del reel, sintetizados desde cero.

Lee build/cues.json (lo genera `node tools/render.mjs --cues` desde main.js),
así cada efecto cae exactamente en su cuadro. Salida: build/audio.wav
(48 kHz, estéreo, -14 LUFS integrados, pico real < -1 dBTP).

Idea sonora:
  · El malestar se escucha: un tono tenso y un latido que suben con la curva
    y se cortan de golpe en cada "evitás" (y ahí entra un acorde de alivio).
  · Gancho: tensión → exhalación de alivio → entra el ritmo en "te está entrenando".
  · Mañana: más grave, latido más fuerte, alarma. Golpe seco al pasar al "mundo".
  · El mundo se achica: cajita de música sola, cada tachón baja un escalón.
  · La cuenta: pitido de posnet, impresora de ticket y papel que se corta.
  · Andá con miedo: la armonía pasa a mayor; cada exposición suena más suave.
"""
import json
import sys
import wave
from pathlib import Path

import numpy as np
from scipy import signal

ROOT = Path(__file__).resolve().parent.parent
SR = 48_000
DUR = 60.0
N = int(SR * DUR)
BPM = 96
BEAT = 60 / BPM            # 0,625 s
BAR = 4 * BEAT             # 2,5 s
ORIGIN = -0.08             # el compás 1 cae en 2,42 s, cuando entra "Ese alivio"
rng = np.random.default_rng(611)

C = json.loads((ROOT / 'build' / 'cues.json').read_text())


def bar(k, beat=0.0):
    return ORIGIN + k * BAR + beat * BEAT


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def tt(n):
    return np.arange(n) / SR


def clamp(x, a=0.0, b=1.0):
    return np.minimum(b, np.maximum(a, x))


def env_ad(n, att, dec):
    t = tt(n)
    return np.minimum(1, t / max(att, 1e-4)) * np.exp(-t / dec)


def bp(x, lo, hi, order=2):
    return signal.sosfilt(signal.butter(order, [lo, hi], 'bp', fs=SR, output='sos'), x)


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, 'lp', fs=SR, output='sos'), x)


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, 'hp', fs=SR, output='sos'), x)


class Bus:
    def __init__(self, tail=4.0):
        self.x = np.zeros((2, N + int(tail * SR)))

    def add(self, sig, t, pan=0.0, gain=1.0):
        i = int(round(t * SR))
        if sig.ndim == 1:
            a = (pan + 1) * np.pi / 4
            sig = np.vstack([sig * np.cos(a), sig * np.sin(a)]) * np.sqrt(2)
        if i < 0:
            sig, i = sig[:, -i:], 0
        n = min(sig.shape[1], self.x.shape[1] - i)
        if n > 0:
            self.x[:, i:i + n] += sig[:, :n] * gain


music, drums, fx, verb_send = Bus(), Bus(), Bus(), Bus()


# ------------------------------------------------------------------ instrumentos
def rhodes(f, dur, vel=0.7):
    rel = 0.4
    n = int((dur + rel) * SR)
    t = tt(n)
    tau = 1.6 * (260 / f) ** 0.45
    amp = np.exp(-t / tau) * np.minimum(1, t / 0.004)
    off = t > dur
    amp[off] *= np.exp(-(t[off] - dur) / 0.13)
    idx = (0.7 + 1.5 * vel) * np.exp(-t / 0.28) + 0.35
    s = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * t))
    s += 0.14 * vel * np.sin(2 * np.pi * f * 7.02 * t) * np.exp(-t / 0.025)
    trem = 1 + 0.12 * np.sin(2 * np.pi * 4.6 * t)
    return s * amp * vel * trem


def chord_rhodes(notes, t0, dur, vel=0.6, spread=0.012, bus=None, gain=1.0):
    bus = bus or music
    for i, m in enumerate(notes):
        pan = -0.35 + 0.7 * i / max(1, len(notes) - 1)
        bus.add(rhodes(mtof(m), dur, vel * (0.85 + 0.15 * rng.random())), t0 + i * spread, pan, 0.16 * gain)


def pad(notes, dur, att=0.8, rel=1.6, bright=1800, gain=1.0):
    n = int((dur + rel) * SR)
    t = tt(n)
    e = clamp(t / att) ** 2 * np.where(t > dur, np.exp(-(t - dur) / (rel / 3)), 1)
    out = np.zeros((2, n))
    for m in notes:
        f = mtof(m)
        for v, cents in enumerate((-8, 0, 7)):
            fv = f * 2 ** (cents / 1200) * (1 + 0.002 * np.sin(2 * np.pi * (0.18 + 0.05 * v) * t + v))
            ph = 2 * np.pi * np.cumsum(fv) / SR + rng.uniform(0, 6.28)
            saw = sum(np.sin(k * ph) / k for k in range(1, 7))
            out[v % 2] += saw
    out = np.vstack([lp(ch, bright) for ch in out])
    return out * e * gain / (len(notes) * 3)


def bass(f, dur, vel=0.8):
    n = int((dur + 0.15) * SR)
    t = tt(n)
    e = np.minimum(1, t / 0.008) * np.exp(-t / 1.2) * np.where(t > dur, np.exp(-(t - dur) / 0.05), 1)
    s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.1 * np.sin(6 * np.pi * f * t)
    return np.tanh(1.5 * s) / np.tanh(1.5) * e * vel


def marimba(f, vel=0.6, dur=0.7):
    t = tt(int(dur * SR))
    s = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.32) + 0.22 * np.sin(2 * np.pi * f * 3.93 * t) * np.exp(-t / 0.04)
    return s * np.minimum(1, t / 0.002) * vel


def musicbox(f, vel=0.5):
    t = tt(int(2.2 * SR))
    s = (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.9) + 0.4 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t / 0.35)
         + 0.25 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t / 0.08))
    return s * np.minimum(1, t / 0.001) * vel


def kick(vel=1.0):
    t = tt(int(0.45 * SR))
    fr = 50 + 95 * np.exp(-t / 0.028)
    s = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t / 0.22)
    s += rng.normal(0, 1, t.size) * np.exp(-t / 0.003) * 0.1
    return lp(s, 4000) * vel


def rim(vel=0.6):
    t = tt(int(0.12 * SR))
    s = (np.sin(2 * np.pi * 1650 * t) + 0.6 * np.sin(2 * np.pi * 520 * t)) * np.exp(-t / 0.012)
    s += bp(rng.normal(0, 1, t.size), 1500, 6000) * np.exp(-t / 0.02) * 0.6
    return s * vel


def clap(vel=0.6):
    n = int(0.3 * SR)
    t = tt(n)
    e = np.zeros(n)
    for d in (0, 0.009, 0.019):
        e += np.where(t >= d, np.exp(-(t - d) / 0.008), 0)
    e += np.exp(-t / 0.09) * 0.5
    return bp(rng.normal(0, 1, n), 900, 5200) * e * vel * 0.6


def hat(vel=0.4, open_=False):
    n = int((0.35 if open_ else 0.07) * SR)
    t = tt(n)
    s = hp(rng.normal(0, 1, n), 7000, 4) * np.exp(-t / (0.12 if open_ else 0.016))
    return s * vel


def shaker(vel=0.35):
    n = int(0.11 * SR)
    t = tt(n)
    return bp(rng.normal(0, 1, n), 4500, 11000) * np.minimum(1, t / 0.015) * np.exp(-t / 0.03) * vel


def heartbeat(vel=1.0):
    def thump(f0, d):
        t = tt(int(0.3 * SR))
        fr = f0 * (1 + 0.6 * np.exp(-t / 0.02))
        return np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.minimum(1, t / 0.006) * np.exp(-t / d)
    a, b = thump(58, 0.09), thump(50, 0.07) * 0.7
    out = np.zeros(int(0.5 * SR))
    out[:a.size] += a
    i = int(0.17 * SR)
    out[i:i + b.size] += b[:out.size - i]
    return lp(out, 300) * vel


# ------------------------------------------------------------------ efectos
def noise(n):
    return rng.normal(0, 1, n)


def marker(dur=0.32):
    """marcador sobre papel: frote áspero + chillido de la punta."""
    n = int(dur * SR)
    t = tt(n)
    strokes = 0.5 + 0.5 * np.sin(2 * np.pi * 9 * t + 2 * np.sin(2 * np.pi * 3 * t)) ** 2
    rub = bp(noise(n), 1800, 6500) * strokes * 0.55
    sq = np.sin(2 * np.pi * np.cumsum(1350 + 260 * np.sin(2 * np.pi * 5.5 * t)) / SR) * 0.18
    e = np.minimum(1, t / 0.02) * np.minimum(1, (dur - t) / 0.06)
    return (rub + sq * strokes) * e


def pen(dur=0.5, seed=0):
    """birome sobre papel: rasguños cortos e irregulares."""
    g = np.random.default_rng(seed)
    n = int(dur * SR)
    t = tt(n)
    gate = np.zeros(n)
    x = 0
    while x < n:
        L = int(g.uniform(0.03, 0.09) * SR)
        gate[x:x + L] = np.hanning(min(L, n - x)) * g.uniform(0.5, 1)
        x += L + int(g.uniform(0.005, 0.03) * SR)
    s = bp(g.normal(0, 1, n), 2500, 9000) * gate
    return s * np.minimum(1, (dur - t) / 0.05).clip(0, 1) * 0.5


def exhale(dur=1.0):
    """exhalación de alivio: aire con formantes que baja."""
    n = int(dur * SR)
    t = tt(n)
    x = noise(n)
    a = bp(x, 380, 900) * 0.9 + bp(x, 1100, 2400) * 0.5 + bp(x, 2600, 5200) * 0.25
    e = np.minimum(1, t / 0.07) ** 1.5 * np.exp(-t / (dur * 0.42))
    return lp(a * e, 5200) * 0.9


def swoosh(dur=0.42, up=False):
    n = int(dur * SR)
    t = tt(n)
    f, frames, Z = signal.stft(noise(n), SR, nperseg=1024)
    u = np.clip(frames / dur, 0, 1)
    fc = np.exp(np.interp(u, [0, 1], np.log([500, 5200]) if up else np.log([4200, 380])))
    mask = np.exp(-((np.log(f[:, None] + 1) - np.log(fc[None, :])) / 0.5) ** 2)
    _, y = signal.istft(Z * mask, SR, nperseg=1024)
    y = y[:n]
    e = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.6
    return y * e * 2.2


def thud(vel=1.0, f0=95):
    t = tt(int(0.35 * SR))
    fr = f0 * (0.6 + 0.4 * np.exp(-t / 0.05))
    s = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t / 0.16)
    s += bp(noise(t.size), 200, 2000) * np.exp(-t / 0.01) * 0.3
    return s * vel


def tick(vel=0.5):
    t = tt(int(0.06 * SR))
    return (np.sin(2 * np.pi * 2300 * t) * np.exp(-t / 0.006) + 0.5 * np.sin(2 * np.pi * 780 * t) * np.exp(-t / 0.01)) * vel


def blip(f0, f1, dur=0.05, vel=0.4):
    t = tt(int(dur * SR))
    f = np.geomspace(f0, f1, t.size)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / dur) * vel


def stamp():
    t = tt(int(0.25 * SR))
    s = np.sin(2 * np.pi * np.cumsum(70 + 60 * np.exp(-t / 0.02)) / SR) * np.exp(-t / 0.08)
    s += bp(noise(t.size), 400, 3500) * np.exp(-t / 0.015) * 0.8
    return s


def drop_whoosh():
    """caída: un barrido que baja + un golpe grave suave (la "panza" del alivio)."""
    dur = 0.55
    t = tt(int(dur * SR))
    f = np.geomspace(900, 70, t.size)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.25) * 0.5
    return s + swoosh(dur)[:t.size] * 0.5


def riser(dur=0.62):
    n = int(dur * SR)
    t = tt(n)
    f = np.geomspace(180, 900, n)
    bub = np.sin(2 * np.pi * np.cumsum(f * (1 + 0.04 * np.sin(2 * np.pi * 22 * t))) / SR)
    return (bub * 0.35 + swoosh(dur, up=True)[:n] * 0.6) * np.sin(np.pi * t / dur) ** 0.8


def alarm():
    """despertador digital, bajito: bip-bip, bip-bip."""
    out = np.zeros(int(1.3 * SR))
    for k, d in enumerate((0, 0.14, 0.62, 0.76)):
        t = tt(int(0.09 * SR))
        s = np.sign(np.sin(2 * np.pi * 2050 * t)) * 0.5 + np.sin(2 * np.pi * 4100 * t) * 0.2
        s = lp(s, 6000) * np.minimum(1, t / 0.004) * np.minimum(1, (0.09 - t) / 0.006)
        i = int(d * SR)
        out[i:i + s.size] += s
    return out


def hit():
    t = tt(int(2.2 * SR))
    boom = np.sin(2 * np.pi * np.cumsum(38 + 70 * np.exp(-t / 0.06)) / SR) * np.exp(-t / 0.6)
    crack = bp(noise(t.size), 300, 4000) * np.exp(-t / 0.05) * 0.5
    low_piano = np.zeros(t.size)
    lp_ = rhodes(mtof(26), 1.6, 0.9)[:t.size]
    low_piano[:lp_.size] = lp_ * 0.8
    return boom + crack + low_piano


def pop(f0=320, f1=1100):
    return blip(f0, f1, 0.07, 0.7)


def womp(step):
    """el mundo baja un escalón: un tono que cae, cada vez más grave."""
    dur = 0.42
    t = tt(int(dur * SR))
    f0 = mtof(62 - step * 3)
    f = f0 * np.geomspace(1, 0.62, t.size)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.3 * np.sin(4 * np.pi * np.cumsum(f) / SR)
    return s * np.minimum(1, t / 0.01) * np.exp(-t / 0.18) * 0.7


def scratch():
    return pen(0.3, seed=int(rng.integers(1e6))) * 1.8


def card_beep():
    out = np.zeros(int(0.4 * SR))
    for d in (0, 0.16):
        t = tt(int(0.1 * SR))
        s = np.sin(2 * np.pi * 1850 * t) * np.minimum(1, t / 0.003) * np.minimum(1, (0.1 - t) / 0.005)
        out[int(d * SR):int(d * SR) + s.size] += s * 0.5
    return out


def printer_line(dur=0.3):
    """impresora térmica/de matriz: zumbido con dientes + motorcito."""
    n = int(dur * SR)
    t = tt(n)
    teeth = (np.sin(2 * np.pi * 118 * t) > 0.3).astype(float)
    buzz = bp(noise(n), 1500, 6000) * teeth * 0.45
    motor = np.sin(2 * np.pi * np.cumsum(330 + 30 * np.sin(2 * np.pi * 7 * t)) / SR) * 0.12
    e = np.minimum(1, t / 0.01) * np.minimum(1, (dur - t) / 0.02)
    return (buzz + motor) * e


def tear():
    n = int(0.38 * SR)
    t = tt(n)
    crackle = np.zeros(n)
    idx = rng.integers(0, n, 180)
    crackle[idx] = rng.uniform(-1, 1, idx.size)
    s = bp(crackle, 800, 7000) * 3 + bp(noise(n), 1500, 7000) * 0.25
    return s * np.minimum(1, t / 0.02) * np.exp(-t / 0.2)


def slide_down():
    dur = 0.5
    t = tt(int(dur * SR))
    f = np.geomspace(1150, 260, t.size) * (1 + 0.025 * np.sin(2 * np.pi * 11 * t))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.15 * np.sin(4 * np.pi * np.cumsum(f) / SR)
    return s * np.minimum(1, t / 0.02) * np.minimum(1, (dur - t) / 0.08) * 0.45


# ------------------------------------------------------------------ el malestar se escucha
def anxiety_series():
    """malestar (0–12,5) a frecuencia de audio; -1 donde no hay curva."""
    a = np.array(C['anx'], dtype=float)
    tA = np.arange(a.size) / C['anxRate']
    # gancho: el medidor está en 8 y cae a 2 con el alivio
    hook = (tA < 1.6)
    v_hook = np.where(tA < 1.0, 7.6 + 0.4 * tA, 8 - 6 * clamp((tA - 1.0) / 0.26))
    a = np.where(hook, v_hook, a)
    gate = (a >= 0).astype(float)
    gate[(tA > 1.26) & (tA < 1.6)] = np.clip(1 - (tA[(tA > 1.26) & (tA < 1.6)] - 1.26) / 0.34, 0, 1)
    tS = tt(N)
    v = np.interp(tS, tA, np.maximum(a, 0))
    g = np.interp(tS, tA, gate)
    g = signal.sosfiltfilt(signal.butter(1, 12, 'lp', fs=SR, output='sos'), g)
    return v, np.clip(g, 0, 1)


def anxiety_voice(v, g):
    """tono tenso: un acorde disonante que sube con el malestar y tiembla más rápido."""
    out = np.zeros((2, N))
    base = mtof(45 + v * 1.85)
    flutter = 1 + 0.004 * v * np.sin(2 * np.pi * np.cumsum(3 + 0.6 * v) / SR)
    for ratio, pan, w in ((1.0, -0.3, 1.0), (2 ** (1 / 12), 0.3, 0.55), (1.5, 0.0, 0.35), (2.0, 0.0, 0.25)):
        ph = 2 * np.pi * np.cumsum(base * ratio * flutter) / SR
        saw = sum(np.sin(k * ph) / k for k in range(1, 8))
        a = (pan + 1) * np.pi / 4
        out[0] += saw * w * np.cos(a)
        out[1] += saw * w * np.sin(a)
    # el filtro se abre con el malestar (más brillo = más tensión)
    cut = 260 + 160 * v
    blocks = int(np.ceil(N / 2400))
    y = np.zeros_like(out)
    zi = None
    for b in range(blocks):
        s0, s1 = b * 2400, min(N, (b + 1) * 2400)
        sos = signal.butter(2, float(np.clip(cut[s0], 80, 9000)), 'lp', fs=SR, output='sos')
        if zi is None:
            zi = np.zeros((2, sos.shape[0], 2))
        for ch in range(2):
            y[ch, s0:s1], zi[ch] = signal.sosfilt(sos, out[ch, s0:s1], zi=zi[ch])
    level = np.minimum(0.62, 0.01 + 0.052 * np.clip(v - 1.6, 0, 12) ** 1.12) * g
    return y * level


def heartbeat_track(v, g):
    tS = np.arange(N) / SR
    t = 0.05
    while t < DUR:
        i = int(t * SR)
        if g[i] > 0.15:
            vel = (0.35 + 0.06 * v[i]) * g[i]
            drums.add(heartbeat(min(1.2, vel)), t, 0, 0.9)
            t += 60 / (62 + 7.5 * v[i])
        else:
            t += 0.05


def ghost_track():
    """lo que no ves: un tono aireado que sigue la curva fantasma (sube, toca techo, baja)."""
    t0, d = 21.0, 2.6
    n = int((d + 1.2) * SR)
    t = tt(n)
    u = np.clip(t / d, 0, 1)
    gu = -(np.cos(np.pi * u) - 1) / 2
    gx = 470 + 482 * gu
    gv = np.where(gx <= 560, 8.0 + 0.55 * np.sin(np.pi / 2 * (gx - 470) / 90),
                  2.4 + 6.15 * np.exp(-np.power(np.maximum(gx - 560, 0) / 205, 1.6)))
    f = mtof(45 + gv * 1.85)
    ph = 2 * np.pi * np.cumsum(f * (1 + 0.006 * np.sin(2 * np.pi * 5 * t))) / SR
    s = np.sin(ph) + 0.3 * np.sin(2 * ph)
    dash = 0.55 + 0.45 * (np.sin(2 * np.pi * 7 * t) > -0.2)       # como el trazo punteado
    e = np.minimum(1, t / 0.3) * np.where(t > d, np.exp(-(t - d) / 0.35), 1)
    air = bp(noise(n), 900, 4000) * 0.15
    return (s * dash + air) * e * 0.16


# ------------------------------------------------------------------ armonía y ritmo
CH = {
    'Dm9': [50, 53, 57, 60, 64], 'Bbmaj7': [46, 53, 57, 62], 'Gm9': [43, 50, 53, 57, 62],
    'A7sus': [45, 50, 55, 64], 'A7': [45, 49, 55, 64], 'Fmaj9': [41, 57, 60, 64, 67],
    'Fmaj7': [41, 53, 57, 60, 64], 'C/E': [40, 55, 60, 64], 'Dm7': [38, 53, 57, 60, 62],
    'Gm7': [43, 53, 58, 62], 'C7': [36, 52, 58, 64], 'C6': [36, 52, 57, 64], 'Dm': [38, 53, 57, 62],
    'Bb/D': [38, 53, 58, 62],
}


def root(name):
    return CH[name][0]


def comp(name, t0, dur, vel=0.55, pattern='syn', gain=1.0):
    """rhodes: acorde en el 1 y anticipación en el "y" del 2 (pattern syn) o redondas (pad)."""
    notes = CH[name][1:]
    if pattern == 'syn':
        chord_rhodes(notes, t0, BEAT * 1.4, vel, gain=gain)
        if dur > 2 * BEAT:
            chord_rhodes(notes, t0 + 1.5 * BEAT, BEAT * 1.6, vel * 0.8, gain=gain)
    else:
        chord_rhodes(notes, t0, dur * 0.95, vel, gain=gain)


def bassline(name, t0, dur, vel=0.8, busy=False, gain=1.0):
    r = root(name)
    while r > 40:
        r -= 12
    f = mtof(r)
    music.add(bass(f, BEAT * 1.6, vel), t0, 0, 0.5 * gain)
    if busy:
        music.add(bass(f, BEAT * 0.4, vel * 0.7), t0 + 2.5 * BEAT, 0, 0.45 * gain)
        music.add(bass(f * 2, BEAT * 0.4, vel * 0.6), t0 + 3.5 * BEAT, 0, 0.4 * gain)
    elif dur > 2.5 * BEAT:
        music.add(bass(f, BEAT * 0.9, vel * 0.7), t0 + 2.5 * BEAT, 0, 0.42 * gain)


def groove(t0, t1, kick_v=0.9, snare='rim', hats=True, hat_v=0.28, swing=0.03, four=False, gain=1.0):
    k = 0
    t = t0
    while t < t1 - 1e-6:
        beat_in_bar = k % 4
        if beat_in_bar in (0, 2) or four:
            drums.add(kick(kick_v), t, 0, 0.75 * gain)
        if beat_in_bar in (1, 3) and snare:
            drums.add(rim(0.55) if snare == 'rim' else clap(0.7), t, 0.1, 0.5 * gain)
        if hats:
            drums.add(hat(hat_v * (1 if beat_in_bar % 2 == 0 else 0.8)), t, 0.25, 0.55 * gain)
            drums.add(hat(hat_v * 0.6), t + BEAT / 2 + swing, 0.25, 0.55 * gain)
        k += 1
        t += BEAT


def score():
    v, g = anxiety_series()
    music.x[:, :N] += anxiety_voice(v, g)
    heartbeat_track(v, g)

    # 0 · gancho A: sólo tensión (arriba) y alivio
    music.add(pad(CH['Fmaj9'][1:], 1.2, att=0.25, rel=1.6, bright=2600, gain=1.1), 1.0, 0, 0.9)
    chord_rhodes(CH['Fmaj9'][1:], 1.02, 1.2, 0.5, spread=0.03)

    # 1 · gancho B: entra el ritmo
    groove(bar(1), bar(2), hat_v=0.3)
    comp('Dm9', bar(1), BAR)
    bassline('Dm9', bar(1), BAR, busy=True)

    # 2–4 · qué es: groove liviano + marimba
    for k, ch in zip((2, 3, 4), ('Bbmaj7', 'Gm9', 'A7sus')):
        comp(ch, bar(k), BAR, 0.5)
        bassline(ch, bar(k), BAR)
        notes = CH[ch][1:]
        for j in range(8):
            m = notes[(j * 2) % len(notes)] + 12
            music.add(marimba(mtof(m), 0.45 if j % 2 == 0 else 0.3), bar(k, j * 0.5), 0.3 - 0.6 * (j % 2), 0.11)
    chord_rhodes(CH['A7'][1:], bar(4, 2.5), BEAT * 1.4, 0.45)
    groove(bar(2), bar(5) - 0.4, kick_v=0.7, hat_v=0.22, gain=0.8)

    # 5–7 · hoy: casi todo se va; queda el malestar, el latido y un pedal
    music.add(pad([38, 45, 50, 53], 15.62 - bar(5), att=1.0, rel=0.25, bright=900, gain=1.0), bar(5), 0, 0.7)
    for k in (5, 6):
        drums.add(kick(0.55), bar(k), 0, 0.5)
    # alivio: acorde mayor que abre todo
    music.add(pad(CH['Fmaj9'][1:], 4.0, att=0.12, rel=2.0, bright=3200, gain=1.2), 15.66, 0, 0.8)
    chord_rhodes(CH['Fmaj9'][1:], 15.68, 2.2, 0.55, spread=0.04)
    music.add(bass(mtof(29), 2.4, 0.7), 15.7, 0, 0.45)
    groove(bar(7) - 0.0, bar(8), kick_v=0.5, snare=None, hat_v=0.18, gain=0.7)

    # 8–10 · lo que no ves: armonía suave, sin batería
    for k, ch in zip((8, 9, 10), ('Bbmaj7', 'Gm9', 'Bbmaj7')):
        comp(ch, bar(k), BAR, 0.38, pattern='pad', gain=0.9)
        music.add(pad(CH[ch][1:], BAR, att=0.6, rel=1.0, bright=1400, gain=0.8), bar(k), 0, 0.6)
        bassline(ch, bar(k), BAR, 0.6, gain=0.8)
        for j in range(8):
            drums.add(shaker(0.25 if j % 2 else 0.35), bar(k, j * 0.5), -0.3, 0.5)
    chord_rhodes(CH['A7sus'][1:], bar(10, 2), BEAT * 2, 0.4)
    music.add(ghost_track(), 21.0, 0.15, 1.0)

    # 11–13 · mañana: más grave, pulso de bajo en corcheas, alarma
    for k, ch in zip((11, 12, 13), ('Dm', 'Bb/D', 'Dm')):
        music.add(pad(CH[ch][1:], BAR, att=0.4, rel=0.4, bright=1100, gain=0.9), bar(k), 0, 0.65)
        r = mtof(26)
        for j in range(8):
            music.add(bass(r, BEAT * 0.4, 0.7 if j % 2 == 0 else 0.5), bar(k, j * 0.5), 0, 0.42)
        drums.add(kick(0.75), bar(k), 0, 0.6)
        drums.add(kick(0.6), bar(k, 2), 0, 0.55)
    fx.add(alarm(), 28.65, 0.4, 0.13)
    fx.add(alarm(), 31.05, -0.4, 0.2)
    for td, sc in ((30.62, 0.7), (32.17, 0.45)):      # cada alivio dura menos
        music.add(pad(CH['Fmaj9'][1:], 0.9, att=0.08, rel=0.9, bright=2600, gain=1.0), td, 0, 0.6 * sc)
        chord_rhodes(CH['Fmaj9'][1:], td + 0.02, 0.8, 0.45 * sc, spread=0.03)
    fx.add(riser(1.5), 33.5, 0, 0.5)

    # 14–16 · el mundo se achica: golpe, silencio y cajita de música sola
    fx.add(hit(), 35.0, 0, 0.75)
    music.add(pad([38, 50, 53, 57], 6.0, att=1.5, rel=1.0, bright=800, gain=0.9), 35.4, 0, 0.55)
    mb = [74, 72, 69, 65, 69, 67, 65, 62, 64, 65, 62, 57]
    for j, m in enumerate(mb):
        music.add(musicbox(mtof(m), 0.45), 35.6 + j * BEAT * 0.75, 0.35 * np.sin(j), 0.13)

    # 16,5–18 · la cuenta: groove juguetón (ii–V–I en Fa)
    t7 = bar(16, 2)
    for t0, ch, d in ((t7, 'Gm7', BAR / 2), (bar(17), 'C7', BAR), (bar(18), 'Fmaj7', BAR)):
        comp(ch, t0, d, 0.5)
        bassline(ch, t0, d, 0.75, busy=d >= BAR)
    groove(t7, bar(19) - 0.3, kick_v=0.8, snare='clap', hat_v=0.26)

    # 19–21 · andá con miedo: mayor, cálido, sin apuro
    for k, ch in zip((19, 20, 21), ('Fmaj7', 'C/E', 'Dm7')):
        comp(ch, bar(k), BAR, 0.5)
        music.add(pad(CH[ch][1:], BAR, att=0.5, rel=1.0, bright=2200, gain=0.9), bar(k), 0, 0.55)
        bassline(ch, bar(k), BAR, 0.7)
    comp('Fmaj7', 47.15, bar(19) - 47.15, 0.4, pattern='pad')
    groove(bar(19), bar(22), kick_v=0.6, snare='rim', hat_v=0.18, gain=0.75)
    # cada exposición: una ola de rhodes que sube y baja, cada vez más chica
    h = C['humps']
    for i, A in enumerate(h['A']):
        t0 = h['t0'] + i * h['dt']
        top = 69 + A * 1.3
        for j, m in enumerate((62, 65, round(top), 65)):
            music.add(rhodes(mtof(m), 0.35, 0.25 + 0.06 * A), t0 + j * 0.13, 0.3 * (j - 1.5), 0.12)

    # 22–23 · cierre: Bb – C – Fa y queda sonando
    comp('Bbmaj7', bar(22), BAR / 2, 0.55)
    comp('C6', bar(22, 2), BAR / 2, 0.55)
    bassline('Bbmaj7', bar(22), BAR / 2, 0.75)
    music.add(bass(mtof(36), BAR / 2, 0.75), bar(22, 2), 0, 0.5)
    groove(bar(22), bar(23), kick_v=0.7, snare='rim', hat_v=0.22)
    music.add(pad(CH['Fmaj9'][1:], 2.3, att=0.2, rel=1.2, bright=2600, gain=1.1), bar(23), 0, 0.7)
    chord_rhodes(CH['Fmaj9'][1:], bar(23), 2.2, 0.6, spread=0.05)
    music.add(bass(mtof(29), 2.2, 0.7), bar(23), 0, 0.5)
    drums.add(kick(0.8), bar(23), 0, 0.6)


def sfx():
    seed = 0
    ROWS = C['ticket']
    shrink_n = 0
    for name, t in C['cues']:
        seed += 1
        if name == 'marker':
            fx.add(marker(), t, 0.1, 0.5)
        elif name == 'pen':
            fx.add(pen(0.55, seed), t, -0.2, 0.35)
        elif name == 'exhale':
            fx.add(exhale(1.05 if t < 2 else 0.8), t, 0, 0.75 if t < 2 else 0.5)
        elif name == 'meter':
            for i in range(6):
                fx.add(blip(1200 - i * 130, 1100 - i * 130, 0.035, 0.35), t + i * 0.042, 0.4 - 0.15 * i, 0.5)
        elif name == 'swoosh':
            fx.add(swoosh(), t - 0.1, 0, 0.32)
        elif name == 'thud':
            fx.add(thud(0.9), t, 0, 0.55)
        elif name == 'tick':
            fx.add(tick(0.6), t, 0.2, 0.4)
        elif name == 'rise':
            fx.add(riser(), t, 0, 0.45)
        elif name == 'stamp':
            fx.add(stamp(), t, 0, 0.5)
        elif name == 'drop':
            fx.add(drop_whoosh(), t, 0, 0.55)
        elif name == 'pop':
            fx.add(pop(), t, 0, 0.4)
        elif name == 'scratch':
            fx.add(scratch(), t, 0.15, 0.5)
        elif name == 'shrink':
            fx.add(womp(shrink_n), t, 0, 0.45)
            shrink_n += 1
        elif name == 'beep':
            fx.add(card_beep(), t, 0.2, 0.35)
        elif name == 'printer':
            for r in ROWS:
                fx.add(printer_line(0.3), r, 0.1, 0.45)
            fx.add(printer_line(0.25), t, 0.1, 0.35)
        elif name == 'tear':
            fx.add(tear(), t, 0, 0.5)
        elif name == 'shrinkWord':
            fx.add(slide_down(), t, 0, 0.55)


# ------------------------------------------------------------------ mezcla
def reverb(x, secs=1.8, mix=0.18):
    n = int(secs * SR)
    t = tt(n)
    ir = np.vstack([rng.normal(0, 1, n), rng.normal(0, 1, n)]) * np.exp(-t / (secs / 5.5))
    ir = np.vstack([lp(ch, 6500) for ch in ir])
    ir /= np.sqrt((ir ** 2).sum(axis=1, keepdims=True))
    wet = np.vstack([signal.fftconvolve(x[c], ir[c])[:x.shape[1]] for c in range(2)])
    return x + wet * mix


def k_weight(x):
    b1, a1 = [1.53512485958697, -2.69169618940638, 1.19839281085285], [1, -1.69065929318241, 0.73248077421585]
    b2, a2 = [1.0, -2.0, 1.0], [1, -1.99004745483398, 0.99007225036621]
    return signal.lfilter(b2, a2, signal.lfilter(b1, a1, x, axis=-1), axis=-1)


def lufs(x):
    y = k_weight(x)
    blk, hop = int(0.4 * SR), int(0.1 * SR)
    ms = np.array([(y[:, i:i + blk] ** 2).mean(axis=1).sum() for i in range(0, y.shape[1] - blk, hop)])
    L = -0.691 + 10 * np.log10(ms + 1e-12)
    g1 = ms[L > -70]
    rel = -0.691 + 10 * np.log10(g1.mean()) - 10
    g2 = ms[(L > -70) & (L > rel)]
    return -0.691 + 10 * np.log10(g2.mean())


def true_peak(x):
    return np.abs(signal.resample_poly(x, 4, 1, axis=1)).max()


def limiter(x, ceiling):
    look = int(0.004 * SR)
    peak = np.abs(signal.resample_poly(x, 4, 1, axis=1)).max(axis=0)[::4][:x.shape[1]]
    need = np.minimum(1, ceiling / np.maximum(peak, 1e-9))
    # mínimo en ventana de lookahead + liberación suave
    from scipy.ndimage import minimum_filter1d
    g = minimum_filter1d(need, size=2 * look + 1)
    rel = np.exp(-1 / (0.08 * SR))
    out = np.empty_like(g)
    cur = 1.0
    for i in range(g.size):           # liberación exponencial (ataque instantáneo)
        cur = g[i] if g[i] < cur else g[i] + (cur - g[i]) * rel
        out[i] = cur
    out = np.roll(out, -look // 2)
    return x * out


def main():
    score()
    sfx()
    m = reverb(music.x, 2.2, 0.22)
    d = reverb(drums.x, 0.9, 0.08)
    f = reverb(fx.x, 1.2, 0.12)
    mix = m * 0.9 + d * 0.8 + f * 1.0
    mix = mix[:, :N]
    # glue suave
    mix = np.tanh(mix * 1.1) / 1.1
    # micro-fundidos en los extremos (el arranque tiene que tener sonido ya en el cuadro 1)
    mix[:, :int(0.004 * SR)] *= np.linspace(0, 1, int(0.004 * SR))
    mix[:, -int(0.35 * SR):] *= np.linspace(1, 0, int(0.35 * SR)) ** 1.5
    target = -14.0
    for _ in range(3):
        mix *= 10 ** ((target - lufs(mix)) / 20)
        mix = limiter(mix, 10 ** (-1.2 / 20))
    print(f'sonoridad: {lufs(mix):.2f} LUFS · pico real: {20 * np.log10(true_peak(mix)):.2f} dBTP')
    out = ROOT / 'build' / 'audio.wav'
    pcm = (np.clip(mix, -1, 1).T * 32767).astype(np.int16)
    with wave.open(str(out), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(out)


if __name__ == '__main__':
    main()

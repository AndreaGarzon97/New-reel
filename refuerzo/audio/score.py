"""Banda sonora original del reel "Refuerzo intermitente".

Todo se sintetiza acá (sin samples): piano eléctrico FM, colchón de sierras
desafinadas, sub, latido, tic-tac de laboratorio, clics de la pluma, la
tragamonedas y el ciclo tensión → explosión → "luna de miel".
Los eventos salen de cues.json (exportado de la animación), así que el sonido
cae justo en el cuadro.

    python3 score.py            -> score.wav (48 kHz, estéreo, -14 LUFS)
"""
import json
import os

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from pedalboard import (Chorus, Compressor, Delay, Distortion, HighpassFilter, HighShelfFilter, Limiter, LowpassFilter,
                        LowShelfFilter, Pedalboard, PeakFilter, Reverb)
from scipy.signal import butter, resample_poly, sosfilt

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
DUR = 60.0
N = int(SR * DUR)
BEAT = 0.8                     # 75 bpm
rng = np.random.default_rng(1957)

CUES = json.load(open(os.path.join(HERE, 'cues.json')))['cues']


def cues(kind):
    return [c for c in CUES if c['type'] == kind]


# ----------------------------------------------------------------------------
# utilidades
# ----------------------------------------------------------------------------
NOTE = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8,
        'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}


def hz(name):
    n, o = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((NOTE[n] + 12 * (o + 1) - 69) / 12)


def tvec(dur):
    return np.arange(int(dur * SR)) / SR


def sos_filter(x, kind, f, order=2):
    if kind == 'band':
        sos = butter(order, [f[0] / (SR / 2), f[1] / (SR / 2)], 'bandpass', output='sos')
    else:
        sos = butter(order, f / (SR / 2), kind, output='sos')
    return sosfilt(sos, x)


def env_adsr(n, a, d, s, r, hold=None):
    """Envolvente con ataque, decaimiento, sostén y relajación (segundos)."""
    t = np.arange(n) / SR
    hold = (n / SR - r) if hold is None else hold
    e = np.where(t < a, t / max(a, 1e-6), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-6)))
    rel = np.clip(1 - (t - hold) / max(r, 1e-6), 0, 1)
    return e * np.where(t > hold, rel, 1)


class Bus:
    def __init__(self, name):
        self.name = name
        self.x = np.zeros((2, N + SR * 4), dtype=np.float64)

    def add(self, sig, t, gain=1.0, pan=0.0):
        """Suma una señal mono o estéreo en el segundo t con paneo de potencia constante."""
        i = int(round(t * SR))
        if i >= self.x.shape[1]:
            return
        if sig.ndim == 1:
            a = (pan + 1) * np.pi / 4
            sig = np.vstack([sig * np.cos(a), sig * np.sin(a)]) * np.sqrt(2)
        j = min(self.x.shape[1], i + sig.shape[1])
        if i < 0:
            sig, i = sig[:, -i:], 0
        self.x[:, i:j] += gain * sig[:, :j - i]

    def fx(self, board):
        self.x = board(self.x.astype(np.float32), SR).astype(np.float64)
        return self


# ----------------------------------------------------------------------------
# instrumentos
# ----------------------------------------------------------------------------
def ep(f, dur=2.4, vel=0.8, bright=1.0):
    """Piano eléctrico FM (relación 1:1 con índice que decae + 'púa' aguda)."""
    t = tvec(dur)
    idx = (1.1 + 1.4 * vel * bright) * np.exp(-t * 2.6) + 0.18
    mod = np.sin(2 * np.pi * f * t)
    car = np.sin(2 * np.pi * f * t + idx * mod)
    tine = 0.13 * vel * bright * np.sin(2 * np.pi * f * 7.02 * t + 0.7 * mod) * np.exp(-t * 22)
    body = 0.3 * np.sin(2 * np.pi * f * 0.5 * t) * np.exp(-t * 1.6) if f > 300 else 0
    e = np.minimum(1, t / 0.004) * (0.75 * np.exp(-t * 1.25) + 0.25 * np.exp(-t * 0.35))
    rel = np.clip((dur - t) / 0.25, 0, 1)
    return (car + tine + body) * e * rel * vel * 0.5


def polyblep_saw(f, t):
    dt = f / SR
    ph = (np.cumsum(np.full(len(t), dt)) + rng.random()) % 1.0
    s = 2 * ph - 1
    m1 = ph < dt
    x = ph[m1] / dt
    s[m1] -= x + x - x * x - 1
    m2 = ph > 1 - dt
    x = (ph[m2] - 1) / dt
    s[m2] -= x * x + x + x + 1
    return s


def pad_note(f, dur, a=1.2, r=1.8, vel=0.5, bright=1.0):
    """Colchón: dos sierras desafinadas por canal + seno, filtrado."""
    t = tvec(dur + r)
    out = np.zeros((2, len(t)))
    for ch, det in ((0, (-6, 4)), (1, (-3, 7))):
        s = sum(polyblep_saw(f * 2 ** (c / 1200), t) for c in det) * 0.35 + 0.6 * np.sin(2 * np.pi * f * t + ch)
        out[ch] = s
    cut = min(9000, (900 + 1300 * bright) * (1 + f / 900))
    sos = butter(2, cut / (SR / 2), 'low', output='sos')
    out = sosfilt(sos, out, axis=1)
    e = env_adsr(len(t), a, 2.5, 0.8, r, hold=dur)
    return out * e * vel * 0.32


def sub(f, dur, a=0.08, r=0.6, vel=0.6):
    t = tvec(dur + r)
    x = np.sin(2 * np.pi * f * t) + 0.18 * np.sin(4 * np.pi * f * t)
    return np.tanh(1.3 * x) * env_adsr(len(t), a, 3, 0.85, r, hold=dur) * vel * 0.55


def bell(f, dur=2.8, vel=0.6, ratio=3.5):
    t = tvec(dur)
    idx = 2.2 * np.exp(-t * 3.5) + 0.2
    x = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * ratio * t))
    x += 0.35 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t * 2.5)
    e = np.minimum(1, t / 0.002) * np.exp(-t * 1.9)
    return x * e * vel * 0.35


def kick(f0=90, f1=40, dur=0.5, decay=8, vel=1.0, click=0.15):
    t = tvec(dur)
    f = f1 + (f0 - f1) * np.exp(-t * 28)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * decay)
    n = sos_filter(rng.standard_normal(len(t)), 'low', 2500) * np.exp(-t * 300) * click
    x = np.tanh(1.6 * (x + n))
    return x * np.minimum(1, t / 0.002) * vel * 0.8


def heartbeat(vel=0.8):
    a = kick(78, 38, 0.5, 9, vel, 0.05)
    b = kick(70, 36, 0.5, 10, vel * 0.62, 0.04)
    out = np.zeros(int(0.75 * SR))
    out[:len(a)] += a
    k = int(0.21 * SR)
    out[k:k + len(b)] += b[:len(out) - k]
    return sos_filter(out, 'low', 900)


def tick(f=3200, vel=0.5, dur=0.05, ring=0.4):
    t = tvec(dur)
    n = rng.standard_normal(len(t))
    x = sos_filter(n, 'band', (f * 0.7, f * 1.4)) * np.exp(-t * 520)
    x += ring * np.sin(2 * np.pi * f * 0.62 * t) * np.exp(-t * 160)
    return x * vel * 0.6


def wood(f=900, vel=0.6):
    t = tvec(0.09)
    n = sos_filter(rng.standard_normal(len(t)), 'band', (f * 0.6, f * 1.6)) * np.exp(-t * 300)
    x = n + 0.8 * np.sin(2 * np.pi * f * 0.55 * t) * np.exp(-t * 70)
    return x * vel * 0.55


def noise_sweep(dur, f0, f1, q=1.6, shape=None, vel=1.0):
    """Ruido filtrado con un pasabanda que barre de f0 a f1 (filtro de estado variable)."""
    n = int(dur * SR)
    x = rng.standard_normal(n)
    u = np.linspace(0, 1, n)
    fc = f0 * (f1 / f0) ** u
    g = np.tan(np.pi * np.clip(fc, 20, SR * 0.45) / SR)
    k = 1 / q
    y = np.zeros(n)
    ic1 = ic2 = 0.0
    for i in range(n):
        gi = g[i]
        a1 = 1 / (1 + gi * (gi + k))
        v3 = x[i] - ic2
        v1 = a1 * ic1 + gi * a1 * v3
        v2 = ic2 + gi * v1
        ic1 = 2 * v1 - ic1
        ic2 = 2 * v2 - ic2
        y[i] = v1
    e = shape(u) if shape is not None else np.sin(np.pi * u) ** 2
    return y * e * vel * 0.5


def scratch(dur, vel=0.3):
    """Rasguido de pluma sobre papel."""
    n = int(dur * SR)
    x = sos_filter(rng.standard_normal(n), 'band', (2200, 5200))
    m = np.repeat((rng.random(n // 480 + 2) > 0.35) * rng.random(n // 480 + 2), 480)[:n]
    m = sos_filter(m, 'low', 28) * 1.4
    e = np.minimum(1, np.arange(n) / (0.03 * SR)) * np.minimum(1, (n - np.arange(n)) / (0.05 * SR))
    return x * np.clip(m, 0, 1.0) * e * vel * 0.05


def boom(vel=1.0):
    t = tvec(3.0)
    f = 26 + 60 * np.exp(-t * 7)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.6)
    n = sos_filter(rng.standard_normal(len(t)), 'low', 1400) * np.exp(-t * 4.5)
    crack = sos_filter(rng.standard_normal(len(t)), 'band', (1200, 4000)) * np.exp(-t * 26) * 0.22
    y = np.tanh(2.2 * (x * 0.9 + n * 0.7 + crack))
    return y * vel * 0.85


def riser(dur, vel=0.6, f0=200, f1=1600):
    n_sig = noise_sweep(dur, f0 * 2, f1 * 4, q=2.5, shape=lambda u: u ** 2.2, vel=1.0)
    t = tvec(dur)
    f = f0 * (f1 / f0) ** (t / dur)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * (t / dur) ** 2.5 * 0.25
    return (n_sig + tone) * vel


def pop(f0=520, f1=260, vel=0.35, dur=0.09):
    t = tvec(dur)
    f = f1 + (f0 - f1) * np.exp(-t * 60)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 45)
    return x * np.minimum(1, t / 0.001) * vel


# ----------------------------------------------------------------------------
# buses
# ----------------------------------------------------------------------------
pad = Bus('pad')
keys = Bus('keys')
low = Bus('low')
perc = Bus('perc')
sfx = Bus('sfx')
verb_fx = Bus('verb')        # efectos que van con reverb larga


def chord(names, t0, t1, vel=0.45, a=1.2, r=1.8, bright=1.0, bass=None, bass_vel=0.5, spread=0.5):
    for k, nm in enumerate(names):
        pan = (k / max(1, len(names) - 1) - 0.5) * spread * 2
        pad.add(pad_note(hz(nm), t1 - t0, a, r, vel, bright), t0, pan=pan)
    if bass:
        low.add(sub(hz(bass), t1 - t0, 0.25, 0.9, bass_vel), t0)


def arp(notes, t0, t1, step, p=1.0, vel=0.42, jitter_oct=0.0, seed=0, bright=0.8, pattern=None, decay=1.6):
    r = np.random.default_rng(seed)
    seq = pattern or (notes + notes[-2:0:-1])
    k = 0
    t = t0
    while t < t1 - 1e-6:
        nm = seq[k % len(seq)]
        f = hz(nm)
        if jitter_oct and r.random() < jitter_oct:
            f *= 2 if r.random() < 0.5 else 0.5
        if r.random() < p:
            v = vel * (0.75 + 0.35 * r.random())
            keys.add(ep(f, decay, v, bright), t + r.normal(0, 0.004), pan=r.uniform(-0.45, 0.45))
        k += 1
        t += step


# ============================================================================
# PARTITURA
# ============================================================================
# --- S1 · gancho (0–4): espera nocturna -------------------------------------
chord(['D3', 'A3', 'E4', 'F4'], 0.0, 3.9, vel=0.32, a=0.6, r=1.0, bright=0.7, bass='D2', bass_vel=0.32)
keys.add(ep(hz('A4'), 3.0, 0.5, 0.8), 0.05, pan=0.1)
keys.add(ep(hz('D4'), 3.0, 0.4, 0.8), 0.05, pan=-0.1)
for k in range(9):                                   # tic-tac de reloj, la espera
    t = 0.0 + k * 0.4
    if t < 3.45:
        perc.add(tick(2600 if k % 2 == 0 else 2100, 0.22, ring=0.5), t, pan=0.25)
for t in (0.05, 0.85, 1.65, 2.45):                   # latido
    low.add(heartbeat(0.55), t)
for c in cues('bubble_on'):
    sfx.add(pop(480, 300, 0.22), c['t'], pan=-0.3)
for c in cues('bubble_off'):
    sfx.add(pop(300, 170, 0.2, 0.12), c['t'], pan=-0.3)
for c in cues('scribble'):
    sfx.add(scratch(c['d'], 0.55), c['t'], pan=-0.2)

# --- transiciones ------------------------------------------------------------
for c in cues('whoosh'):
    v = c.get('v', 1.0)
    w = noise_sweep(0.75, 180, 4200, q=1.4, shape=lambda u: (np.sin(np.pi * np.clip(u * 1.1, 0, 1)) ** 2), vel=0.55 * v)
    sfx.add(np.vstack([w, np.roll(w, 90)]), c['t'] - 0.1)

# --- S2 · definición (4–10,4): el arpegio que llega "a veces" ----------------
chord(['Bb2', 'F3', 'A3', 'D4'], 4.0, 7.2, vel=0.36, bass='Bb1', bass_vel=0.4)
chord(['G2', 'D3', 'A3', 'Bb3'], 7.2, 10.35, vel=0.36, bass='G1', bass_vel=0.4)
arp(['F4', 'A4', 'D5', 'F5'], 4.0, 7.2, 0.2, p=0.55, vel=0.34, seed=4, pattern=['D5', 'F4', 'A4', 'F5', 'A4', 'D5', 'F4', 'A4'])
arp(['D4', 'G4', 'A4', 'Bb4'], 7.2, 10.0, 0.2, p=0.55, vel=0.34, seed=5, pattern=['Bb4', 'D4', 'G4', 'A4', 'G4', 'Bb4', 'D4', 'G4'])
low.add(kick(70, 34, 0.7, 6, 0.5, 0.05), 4.12)
for c in cues('flick'):
    sfx.add(tick(5200, 0.06 * c.get('v', 1), 0.02, ring=0.0), c['t'], pan=rng.uniform(-0.6, 0.6))
for c in cues('tick'):
    sfx.add(wood(1400, 0.35 * c.get('v', 1)), c['t'], pan=0.2)

# --- S3 · laboratorio (10,4–18,4) --------------------------------------------
T_EXT = cues('extinction')[0]['t']
chord(['D3', 'A3', 'C4', 'F4'], 10.4, T_EXT + 0.1, vel=0.34, a=0.5, bass='D2', bass_vel=0.42)
arp(['D4', 'F4', 'A4', 'C5'], 10.8, T_EXT, 0.2, p=1.0, vel=0.3, seed=6, bright=0.6,
    pattern=['D4', 'A4', 'F4', 'C5', 'A4', 'F4', 'D5', 'A4'])
for k in range(20):                                   # cronómetro del laboratorio
    t = 10.4 + k * 0.4
    if t < 18.3:
        perc.add(tick(3400 if k % 2 == 0 else 2900, 0.16, ring=0.25), t, pan=0.35)
for c in cues('pipA'):
    sfx.add(wood(820, 0.38), c['t'], pan=-0.25)
for c in cues('pipB'):
    sfx.add(wood(1800, 0.32), c['t'], pan=0.2)
    sfx.add(bell(hz('A6'), 0.9, 0.16), c['t'], pan=0.3)
for c in cues('pen'):
    sfx.add(scratch(c['d'], 0.42), c['t'], pan=-0.05)
low.add(kick(60, 30, 1.2, 3.2, 0.7, 0.02), T_EXT)                     # se corta el premio
chord(['D3', 'A3'], T_EXT, 15.5, vel=0.22, a=0.05, r=1.2, bright=0.25, bass='D2', bass_vel=0.3)
chord(['Bb2', 'F3', 'A3', 'D4'], 15.6, 17.2, vel=0.38, a=0.25, bass='Bb1', bass_vel=0.45)
chord(['C3', 'G3', 'D4', 'E4'], 17.2, 18.3, vel=0.38, a=0.3, r=0.25, bass='C2', bass_vel=0.45)
keys.add(ep(hz('F4'), 2.6, 0.45), 15.6, pan=-0.1)
keys.add(ep(hz('A4'), 2.6, 0.4), 15.6, pan=0.1)
keys.add(ep(hz('D5'), 2.6, 0.35), 15.6, pan=0.2)

# --- S4 · tragamonedas (18,4–24) ---------------------------------------------
low.add(kick(55, 32, 0.9, 5, 0.85, 0.2), 18.4)
spin = cues('slot_spin')[0]
stops = [c['t'] for c in cues('slot_stop')]
TS = spin['t']
for i, te in enumerate(stops):                       # matraca de cada rodillo
    t, pos = TS, 0.0
    V = 14.0
    last = 0
    while t < te:
        u = min(1, (t - TS) / 0.28)
        v = V * (u * u * (3 - 2 * u)) if t < te - 0.3 else V * (1 - 0.8 * min(1, (t - (te - 0.3)) / 0.3))
        pos += v / SR * 24
        if int(pos) > last:
            last = int(pos)
            sfx.add(tick(1700 + 250 * i, 0.12, 0.03, ring=0.15), t, pan=(i - 1) * 0.5)
        t += 24 / SR
sfx.add(riser(stops[-1] - TS, 0.28, 180, 900), TS)
for c in cues('slot_stop'):
    sfx.add(wood(420, 0.7), c['t'], pan=(c['i'] - 1) * 0.5)
    low.add(kick(80, 45, 0.3, 14, 0.35, 0.1), c['t'])
    if c['sym'] == 'heart':
        verb_fx.add(bell(hz('E6') if c['i'] == 0 else hz('B6'), 1.6, 0.42), c['t'], pan=(c['i'] - 1) * 0.5)
for c in cues('nearmiss'):
    keys.add(ep(hz('E3'), 1.6, 0.4, 0.5), c['t'] + 0.02, pan=0.3)
    keys.add(ep(hz('F3'), 1.6, 0.36, 0.5), c['t'] + 0.04, pan=0.3)
    verb_fx.add(noise_sweep(0.9, 2400, 300, q=1.2, shape=lambda u: np.exp(-u * 3), vel=0.35), c['t'] + 0.05, pan=0.3)
T_ST = [c['t'] for c in cues('hit') if 20 < c['t'] < 22][0]          # aparece la frase de la dopamina
chord(['G2', 'D3', 'A3', 'Bb3', 'D4'], T_ST, 24.0, vel=0.4, a=0.35, bass='G1', bass_vel=0.5)
keys.add(ep(hz('A4'), 2.8, 0.42), T_ST, pan=0.15)
keys.add(ep(hz('D5'), 2.8, 0.34), T_ST + 0.4, pan=-0.15)
keys.add(ep(hz('Bb4'), 2.8, 0.3), T_ST + 1.2, pan=0.1)

# --- S5 · vínculos sanos (24–33,6): estable, cálido --------------------------
prog5 = [(['F3', 'A3', 'C4', 'G4'], 'F2', 24.4, 26.8), (['E3', 'G3', 'C4', 'D4'], 'C2', 26.8, 29.2),
         (['D3', 'F3', 'A3', 'C4'], 'D2', 29.2, 31.6), (['D3', 'F3', 'A3', 'Bb3'], 'Bb1', 31.6, 33.4)]
arps5 = [['F4', 'A4', 'C5', 'G5'], ['E4', 'G4', 'C5', 'D5'], ['D4', 'F4', 'A4', 'C5'], ['D4', 'F4', 'A4', 'Bb4']]
for (ns, b, t0, t1), ap in zip(prog5, arps5):
    chord(ns, t0, t1, vel=0.4, a=0.6, r=1.4, bright=1.1, bass=b, bass_vel=0.5)
    arp(ap, t0 + (0.4 if t0 == 24.4 else 0), t1, 0.4, p=1.0, vel=0.34, seed=int(t0), bright=0.7)
for k in range(12):                                   # pulso estable
    t = 24.4 + k * 0.8
    if t < 33.2:
        low.add(heartbeat(0.42), t)
for c in cues('base_line'):
    low.add(sub(hz('F1'), c['d'] + 0.6, 0.4, 1.0, 0.35), c['t'])
for c in cues('wave'):
    for k, nm in enumerate(['C6', 'A5', 'G5', 'C6', 'F5']):
        verb_fx.add(bell(hz(nm), 2.0, 0.12), c['t'] + k * c['d'] / 5, pan=-0.4 + 0.2 * k)
keys.add(ep(hz('F5'), 2.4, 0.3), 29.4, pan=0.2)

# --- S6 · vínculos tóxicos (33,6–40): la base va y viene ----------------------
chord(['D2', 'Eb2', 'A2'], 33.6, 40.2, vel=0.4, a=0.8, r=1.2, bright=0.45, bass='D1', bass_vel=0.45)
low.add(boom(0.55), 33.75)
arp(['D4', 'Eb4', 'A4', 'D5', 'Bb4'], 34.4, 39.3, 0.2, p=0.42, vel=0.3, jitter_oct=0.25, seed=33, bright=0.9)
for c in cues('toxic_line'):
    sfx.add(scratch(c['d'], 0.55), c['t'], pan=0.0)
for c in cues('peak'):                                 # premio: dulce y breve
    verb_fx.add(bell(hz('F6'), 2.2, 0.32), c['t'], pan=-0.2)
    verb_fx.add(bell(hz('C6'), 2.2, 0.24), c['t'] + 0.03, pan=0.2)
    chord(['F4', 'A4', 'C5'], c['t'], c['t'] + 0.35, vel=0.35, a=0.06, r=0.8, bright=1.3, spread=0.8)
for c in cues('valley'):                               # castigo: golpe sordo y disonancia
    low.add(kick(65, 30, 1.0, 4.0, 0.75, 0.25), c['t'])
    chord(['D2', 'Eb3', 'Ab3'], c['t'], c['t'] + 0.3, vel=0.42, a=0.01, r=0.9, bright=0.6)
irregular = [34.0, 34.62, 35.05, 35.42, 36.3, 36.6, 37.5, 37.92, 38.3, 39.0, 39.25]
for t in irregular:
    low.add(heartbeat(0.32), t)

# --- S6b · ciclo de la violencia (40–47,2) -----------------------------------
tens = [c['t'] for c in cues('tension')]
expl = [c['t'] for c in cues('explosion')]
honey = [c['t'] for c in cues('honeymoon')]
# el zumbido disonante calla en cada "luna de miel": el alivio tiene que sentirse alivio
chord(['D2', 'Eb2'], 40.0, honey[0] - 0.05, vel=0.3, a=1.0, r=0.35, bright=0.35, bass='D1', bass_vel=0.35)
chord(['D2', 'Eb2'], tens[1] - 0.1, honey[1] - 0.05, vel=0.3, a=0.3, r=0.35, bright=0.35, bass='D1', bass_vel=0.3)
for k, (ta, tb) in enumerate(zip(tens, expl)):
    sfx.add(riser(tb - ta + 0.02, 0.5 if k == 0 else 0.35, 140, 1300), ta)
    for j in range(int((tb - ta) / 0.1)):              # el pulso se acelera
        perc.add(tick(1900, 0.06 + 0.05 * j / 10, ring=0.3), ta + j * 0.1 * (1 - 0.25 * j / 10), pan=0.2)
for t in expl:
    low.add(boom(1.0), t)
    verb_fx.add(noise_sweep(1.2, 3000, 200, q=0.9, shape=lambda u: np.exp(-u * 4), vel=0.45), t)
for k, t in enumerate(honey):
    last = k == len(honey) - 1
    dur = 3.4 if last else 0.6
    chord(['F3', 'A3', 'C4', 'G4', 'A4'], t, t + dur, vel=0.42 if last else 0.38, a=0.12, r=2.4 if last else 0.6, bright=1.3,
          bass='F2', bass_vel=0.45, spread=0.8)
    for j, nm in enumerate(['A5', 'C6', 'F6', 'G6']):
        verb_fx.add(bell(hz(nm), 3.0, 0.2 if last else 0.15), t + 0.06 * j, pan=-0.3 + 0.2 * j)
    keys.add(ep(hz('F4'), 3.0, 0.4), t, pan=-0.1)
    keys.add(ep(hz('C5'), 3.0, 0.32), t + 0.02, pan=0.1)
# el alivio se agria: un roce grave que entra despacio debajo del acorde dulce
pad.add(pad_note(hz('E2'), 3.0, a=2.5, r=1.2, vel=0.28, bright=0.3), honey[-1] + 0.6, pan=0)
keys.add(ep(hz('A4'), 2.6, 0.3, 0.6), 44.8, pan=0.2)
keys.add(ep(hz('G4'), 2.6, 0.26, 0.6), 45.6, pan=-0.2)

# --- S7 · la diferencia (47,2–54,4) ------------------------------------------
t_h = cues('healthy_tone')[0]['t']
t_v = cues('violent_tone')[0]['t']
chord(['F3', 'A3', 'C4', 'E4', 'G4'], t_h - 0.3, 54.1, vel=0.36, a=0.7, r=1.2, bright=1.0, bass='F2', bass_vel=0.45)
arp(['F4', 'A4', 'C5', 'E5'], t_h, 54.0, 0.4, p=1.0, vel=0.3, seed=47, bright=0.7)
for k in range(9):
    t = t_h - 0.05 + k * 0.8
    if t < 53.9:
        low.add(heartbeat(0.34), t)
pad.add(pad_note(hz('Db2'), 54.0 - t_v, a=2.0, r=1.0, vel=0.36, bright=0.35), t_v, pan=-0.2)
pad.add(pad_note(hz('D2'), 54.0 - t_v, a=2.4, r=1.0, vel=0.3, bright=0.35), t_v + 0.2, pan=0.2)
low.add(kick(60, 30, 1.0, 4.5, 0.55, 0.2), t_v)
for t in (50.35, 51.0, 51.4, 52.6, 52.85, 53.5):       # golpes irregulares, apagados
    low.add(kick(55, 30, 0.6, 7, 0.3, 0.05), t)

# --- S8 · cierre (54,4–60) -------------------------------------------------------
t_f = cues('final_hit')[0]['t']
low.add(kick(62, 30, 1.4, 3.0, 0.6, 0.05), t_f)
chord(['D3', 'A3', 'E4', 'F4'], t_f, 57.2, vel=0.36, a=0.4, r=1.6, bright=0.8, bass='D2', bass_vel=0.45)
chord(['Bb2', 'F3', 'A3', 'D4'], 57.2, 58.6, vel=0.32, a=0.8, r=1.6, bright=0.7, bass='Bb1', bass_vel=0.38)
for t, nm, v in ((t_f, 'D4', 0.4), (t_f, 'A4', 0.38), (55.6, 'A4', 0.34), (56.4, 'F4', 0.3), (57.2, 'E4', 0.3),
                 (58.0, 'D4', 0.28)):
    keys.add(ep(hz(nm), 3.2, v, 0.7), t, pan=0.1)
for t, v in ((t_f, 0.45), (55.8, 0.36), (57.0, 0.28), (58.4, 0.2)):
    low.add(heartbeat(v), t)
for c in cues('hit'):
    if c['t'] > 4.5:
        low.add(kick(58, 32, 0.8, 5, 0.32 * c.get('v', 1), 0.03), c['t'])

# ============================================================================
# mezcla
# ============================================================================
pad.fx(Pedalboard([HighpassFilter(90), PeakFilter(cutoff_frequency_hz=280, gain_db=-2.5, q=0.8), Chorus(rate_hz=0.25, depth=0.25, centre_delay_ms=8, feedback=0.0, mix=0.4),
                   Reverb(room_size=0.88, damping=0.55, wet_level=0.38, dry_level=0.7, width=1.0)]))
keys.fx(Pedalboard([HighpassFilter(120), LowpassFilter(7500), Delay(delay_seconds=0.6, feedback=0.28, mix=0.2),
                    Reverb(room_size=0.75, damping=0.5, wet_level=0.3, dry_level=0.8, width=1.0)]))
low.fx(Pedalboard([LowpassFilter(1800), Compressor(threshold_db=-14, ratio=2.5, attack_ms=5, release_ms=150)]))
perc.fx(Pedalboard([HighpassFilter(500), Reverb(room_size=0.3, damping=0.6, wet_level=0.12, dry_level=0.9, width=0.6)]))
sfx.fx(Pedalboard([HighpassFilter(80), Reverb(room_size=0.45, damping=0.5, wet_level=0.16, dry_level=0.9, width=0.9)]))
verb_fx.fx(Pedalboard([HighpassFilter(200), Reverb(room_size=0.93, damping=0.4, wet_level=0.45, dry_level=0.6, width=1.0)]))

mix = (pad.x * 0.8 + keys.x * 1.1 + low.x * 0.62 + perc.x * 0.9 + sfx.x * 0.95 + verb_fx.x * 1.0)[:, :N]

# fundido final (el reel vuelve a empezar en silencio)
t = np.arange(N) / SR
mix *= np.clip((DUR - 0.05 - t) / 1.4, 0, 1) ** 1.5
mix *= np.clip(t / 0.01, 0, 1)

master = Pedalboard([HighpassFilter(35), LowShelfFilter(cutoff_frequency_hz=120, gain_db=-4.5, q=0.7),
                     PeakFilter(cutoff_frequency_hz=2600, gain_db=3.0, q=0.7),
                     HighShelfFilter(cutoff_frequency_hz=7000, gain_db=-1.0, q=0.7), Distortion(drive_db=1.0),
                     Compressor(threshold_db=-20, ratio=2.2, attack_ms=20, release_ms=250),
                     Limiter(threshold_db=-3.0, release_ms=120)])
mix = master(mix.astype(np.float32), SR).astype(np.float64)

meter = pyln.Meter(SR)
loud = meter.integrated_loudness(mix.T)
mix = pyln.normalize.loudness(mix.T, loud, -14.0).T
# techo de pico verdadero (-1,2 dBTP) con sobremuestreo x4
for _ in range(4):
    tp = np.max(np.abs(resample_poly(mix, 4, 1, axis=1)))
    ceil = 10 ** (-1.2 / 20)
    if tp <= ceil:
        break
    mix = Limiter(threshold_db=20 * np.log10(ceil / tp) - 0.3, release_ms=80)(mix.astype(np.float32), SR).astype(np.float64)
    mix = pyln.normalize.loudness(mix.T, meter.integrated_loudness(mix.T), -14.0).T
    mix = np.clip(mix, -ceil, ceil)

out = os.path.join(HERE, 'score.wav')
sf.write(out, mix.T.astype(np.float32), SR, subtype='PCM_24')
print('LUFS %.2f  peak %.2f dBFS  ->  %s' % (meter.integrated_loudness(mix.T), 20 * np.log10(np.max(np.abs(mix))), out))

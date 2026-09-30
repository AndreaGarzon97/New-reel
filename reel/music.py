"""Original soft score for the reel: plucked nylon-ish guitar (Karplus-Strong),
round bass, music-box bells and a few tiny foley pops. 80 bpm, 1 bar = 3 s."""
import numpy as np
from scipy.signal import butter, fftconvolve, lfilter

SR = 44100
DUR = 60.0
BPM = 80
BEAT = 60 / BPM
BAR = 4 * BEAT
rng = np.random.default_rng(11)

NOTE = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'Ab': 8, 'A': 9, 'Bb': 10, 'B': 11}


def hz(name):
    n, o = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((NOTE[n] + 12 * (o + 1) - 69) / 12)


def lp(x, fc, order=2):
    b, a = butter(order, fc / (SR / 2))
    return lfilter(b, a, x)


def hp(x, fc, order=1):
    b, a = butter(order, fc / (SR / 2), 'high')
    return lfilter(b, a, x)


def pluck(f, dur=2.6, vel=1.0, bright=0.5, decay=0.9965):
    """Karplus-Strong, synthesised at a rate that makes the period an integer
    (exact tuning) and resampled to SR."""
    N = int(round(SR / f * 2))
    sr2 = N * f
    n = int(dur * sr2)
    exc = rng.uniform(-1, 1, N)
    exc = lp(exc, min(0.95 * sr2 / 2, 1500 + 5000 * bright) * SR / sr2)
    exc -= exc.mean()
    y = np.zeros(n + N + 1)
    y[1:N + 1] = exc
    blocks = n // N + 1
    for k in range(1, blocks):
        s = 1 + k * N
        prev = y[s - N:s]
        prevm1 = y[s - N - 1:s - 1]
        seg = decay * (0.5 * prev + 0.5 * prevm1)
        e = min(s + N, len(y))
        y[s:e] = seg[:e - s]
    y = y[1:n + 1]
    t_src = np.arange(n) / sr2
    t_dst = np.arange(int(dur * SR)) / SR
    out = np.interp(t_dst, t_src, y)
    env = np.minimum(1, t_dst / 0.004) * np.exp(-t_dst * 0.9)
    return out * env * vel


def bell(f, dur=3.0, vel=1.0):
    t = np.arange(int(dur * SR)) / SR
    out = np.zeros_like(t)
    for ratio, amp, dec in [(1, 1.0, 1.6), (2.0, 0.25, 3.0), (3.01, 0.12, 4.5), (5.43, 0.05, 7.0)]:
        out += amp * np.sin(2 * np.pi * f * ratio * t + rng.random()) * np.exp(-t * dec)
    return out * np.minimum(1, t / 0.003) * vel * 0.5


def bass(f, dur=2.4, vel=1.0):
    t = np.arange(int(dur * SR)) / SR
    x = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t) + 0.08 * np.sin(6 * np.pi * f * t)
    env = np.minimum(1, t / 0.012) * np.exp(-t * 1.3)
    return np.tanh(1.4 * x * env) * vel * 0.55


def pop(dur=0.12, f0=900, f1=300, vel=1.0):
    t = np.arange(int(dur * SR)) / SR
    f = f0 + (f1 - f0) * (t / dur)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 38) * vel * 0.5


def swish(dur=0.5, vel=1.0):
    n = int(dur * SR)
    x = rng.uniform(-1, 1, n)
    x = hp(lp(x, 3000), 500)
    t = np.arange(n) / n
    return x * np.sin(np.pi * t) ** 2 * vel * 0.25


mixL = np.zeros(int((DUR + 4) * SR))
mixR = np.zeros_like(mixL)


def add(sig, t, pan=0.0, gain=1.0):
    i = int(max(0, t) * SR)
    e = min(len(mixL), i + len(sig))
    l = np.cos((pan + 1) * np.pi / 4)
    r = np.sin((pan + 1) * np.pi / 4)
    mixL[i:e] += sig[:e - i] * gain * l * 1.41
    mixR[i:e] += sig[:e - i] * gain * r * 1.41


def human(t, amt=0.012):
    return t + rng.normal(0, amt)


# chord per bar: (bass root, voicing for the arpeggio)
CH = {
    'Cmaj7': ('C2', ['C3', 'G3', 'B3', 'E4', 'G4']),
    'Am7': ('A1', ['A2', 'E3', 'G3', 'C4', 'E4']),
    'Fmaj7': ('F1', ['F2', 'C3', 'E3', 'A3', 'C4']),
    'Em7': ('E2', ['E2', 'B2', 'D3', 'G3', 'B3']),
    'Dm7': ('D2', ['D3', 'A3', 'C4', 'F4', 'A4']),
    'Am': ('A1', ['A2', 'E3', 'A3', 'C4', 'E4']),
    'F': ('F1', ['F2', 'C3', 'F3', 'A3', 'C4']),
    'Dm': ('D2', ['D3', 'A3', 'D4', 'F4', 'A4']),
    'E7': ('E2', ['E2', 'B2', 'D3', 'G#3', 'B3']),
    'C/E': ('E2', ['E2', 'C3', 'G3', 'C4', 'E4']),
    'G': ('G1', ['G2', 'D3', 'G3', 'B3', 'D4']),
    'Gsus': ('G1', ['G2', 'D3', 'G3', 'C4', 'D4']),
    'C': ('C2', ['C3', 'G3', 'C4', 'E4', 'G4']),
    'Cadd9': ('C2', ['C3', 'G3', 'D4', 'E4', 'G4']),
}
NOTE['G#'] = 8

SECTIONS = [
    # (first bar, chords, style)
    (0, ['Cmaj7', 'Am7'], 'intro'),
    (2, ['Fmaj7', 'Em7', 'Dm7', 'Em7'], 'sparse'),
    (6, ['Am', 'F', 'Dm', 'E7'], 'tense'),
    (10, ['F', 'C/E', 'Dm7', 'Gsus'], 'warm'),
    (14, ['C', 'Am7', 'Fmaj7', 'G'], 'warm'),
    (18, ['Fmaj7', 'Cadd9'], 'end'),
]

for first, chords, style in SECTIONS:
    for bi, name in enumerate(chords):
        t0 = (first + bi) * BAR
        root, v = CH[name]
        last_bar = style == 'end' and bi == len(chords) - 1
        add(bass(hz(root), 2.8 if not last_bar else 5.0, 0.9), human(t0, 0.004), pan=0.0,
            gain=0.34 if style != 'sparse' else 0.26)
        if style in ('tense', 'warm', 'intro'):
            add(bass(hz(root) * (1.5 if style != 'tense' else 1.0), 1.6, 0.5), human(t0 + 2 * BEAT, 0.006), gain=0.26)
        if last_bar:
            # final strum, slow and open
            for j, nn in enumerate(v):
                add(pluck(hz(nn), 5.5, 0.7, 0.35, 0.9982), t0 + j * 0.055, pan=-0.3 + j * 0.15, gain=0.55)
            for j, nn in enumerate(['C5', 'E5', 'G5', 'C6']):
                add(bell(hz(nn), 4.0, 0.5), t0 + 0.9 + j * 0.28, pan=0.2, gain=0.5)
            continue
        if style == 'sparse':
            pat = [0, None, 2, 3, None, 4, 3, None]
        elif style == 'tense':
            pat = [0, 2, 3, 2, 1, 2, 3, 4]
        elif style == 'intro':
            pat = [0, 2, 3, 4, 1, 3, 4, 3]
        else:
            pat = [0, 2, 3, 4, 1, 3, 4, 2]
        for k, idx in enumerate(pat):
            if idx is None:
                continue
            vel = (0.85 if k % 2 == 0 else 0.62) * rng.uniform(0.85, 1.05)
            if style == 'tense':
                vel *= 0.9
            bright = 0.55 if style != 'sparse' else 0.35
            add(pluck(hz(v[idx]), 2.4, vel, bright), human(t0 + k * BEAT / 2),
                pan=-0.35 + 0.18 * idx, gain=0.5)
        if style == 'tense':
            # soft muted strum on 2 and 4 for a bit of unease
            for beat in (1, 3):
                for j, nn in enumerate(v[1:]):
                    add(pluck(hz(nn), 0.25, 0.35, 0.8, 0.99), human(t0 + beat * BEAT + j * 0.012, 0.003),
                        pan=0.25, gain=0.35)
        if style == 'warm' and first == 10:
            mel = {0: ['A5', None, 'C6', None], 1: ['G5', None, 'E5', None], 2: ['F5', None, 'A5', None],
                   3: ['G5', None, None, None]}[bi]
            for k, nn in enumerate(mel):
                if nn:
                    add(bell(hz(nn), 3.0, 0.45), human(t0 + k * BEAT), pan=0.3, gain=0.45)
        if style == 'intro' and bi == 0:
            add(bell(hz('E5'), 3.0, 0.35), t0 + 0.05, pan=0.3, gain=0.4)

# ---- foley (times match scenes.py)
for t, f0, f1, v in [(0.25, 1100, 500, 0.5), (6 + 2.0, 900, 420, 0.5), (18 + 2.2, 420, 140, 1.0),
                     (30 + 3.1, 1000, 480, 0.5), (30 + 5.2, 1200, 600, 0.45), (6 + 1.3, 700, 350, 0.25)]:
    add(pop(0.14, f0, f1, v), t, pan=0.1, gain=0.8)
add(bell(hz('E6'), 2.0, 0.5), 30 + 8.4, pan=0.0, gain=0.5)
add(bell(hz('G6'), 2.0, 0.35), 30 + 8.52, pan=0.1, gain=0.4)
add(bell(hz('C6'), 2.0, 0.4), 54 + 0.6, pan=0.0, gain=0.4)
add(swish(0.55, 1.0), 42 + 0.2, pan=0.0, gain=0.9)
for k in range(3):  # the three steps get a tiny tick of a pencil
    add(pop(0.05, 2500, 1800, 0.25), 42 + 1.3 + k * 2.3, gain=0.5)

# ---- reverb (small room / plate)
n_ir = int(2.4 * SR)
tt = np.arange(n_ir) / SR
irL = rng.normal(0, 1, n_ir) * np.exp(-tt * 2.6)
irR = rng.normal(0, 1, n_ir) * np.exp(-tt * 2.6)
irL = lp(irL, 5000)
irR = lp(irR, 5000)
irL[:int(0.012 * SR)] = 0
irR[:int(0.017 * SR)] = 0
irL /= np.sqrt((irL ** 2).sum())
irR /= np.sqrt((irR ** 2).sum())
wetL = fftconvolve(mixL, irL)[:len(mixL)]
wetR = fftconvolve(mixR, irR)[:len(mixR)]
L = mixL + 0.32 * wetL
R = mixR + 0.32 * wetR
L, R = hp(L, 35), hp(R, 35)
# gentle glue + warmth
pk = max(np.abs(L).max(), np.abs(R).max())
L, R = np.tanh(1.3 * L / pk) / np.tanh(1.3), np.tanh(1.3 * R / pk) / np.tanh(1.3)
n = int(DUR * SR)
L, R = L[:n], R[:n]
fade = np.ones(n)
fade[:int(0.03 * SR)] = np.linspace(0, 1, int(0.03 * SR))
fade[-int(1.2 * SR):] = np.linspace(1, 0, int(1.2 * SR)) ** 1.5
L *= fade * 0.89
R *= fade * 0.89

from scipy.io import wavfile
wavfile.write('music.wav', SR, (np.stack([L, R], 1) * 32767).astype(np.int16))
print('ok', n / SR)

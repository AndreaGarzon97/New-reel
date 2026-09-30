"""Three alternative original background tracks for the reel, played with
sampled General MIDI instruments (FluidR3 soundfont) instead of synths.
Same form as the reel: 80 bpm, 1 bar = 3 s, sections change at 6/18/30/42/54 s.

    python3 songs.py  ->  ../out/musica/*.mp3
"""
import os
import random
import subprocess

import mido
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter

SF2 = '/usr/share/sounds/sf2/FluidR3_GM.sf2'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out', 'musica')
TMP = os.environ.get('TMPDIR', '/tmp')
TPB = 480
BPM = 80
SR = 44100
DUR = 60.0

# one chord per bar, same harmony as the reel's scenes
FORM = ['Cmaj7', 'Am7',                        # gancho
        'Fmaj7', 'Em7', 'Dm7', 'Em7',          # pasiva
        'Am', 'F', 'Dm', 'E7',                 # agresiva
        'F', 'C/E', 'Dm7', 'G',                # asertiva
        'C', 'Am7', 'Fmaj7', 'G',              # fórmula
        'Fmaj7', 'Cadd9']                      # cierre


def section(bar):
    if bar < 2:
        return 'intro'
    if bar < 6:
        return 'pasiva'
    if bar < 10:
        return 'agresiva'
    if bar < 14:
        return 'asertiva'
    if bar < 18:
        return 'formula'
    return 'cierre'


NAMES = {'C': 0, 'C#': 1, 'D': 2, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'Bb': 10, 'B': 11}


def n(name):
    return NAMES[name[:-1]] + 12 * (int(name[-1]) + 1)


# melody shared (with variations) by the three songs: per bar, (note | None, beats)
MELODY = {
    0: [(None, 1), ('G5', 1), ('E5', 2)],
    1: [('C5', 1.5), ('D5', 0.5), ('E5', 2)],
    2: [('A5', 2), ('G5', 1), ('E5', 1)],
    3: [('G5', 3), (None, 1)],
    4: [('F5', 2), ('E5', 1), ('D5', 1)],
    5: [('E5', 4)],
    6: [('E5', .5), ('E5', .5), ('E5', .5), ('F5', .5), ('E5', 1), ('C5', 1)],
    7: [('C5', .5), ('C5', .5), ('C5', .5), ('D5', .5), ('C5', 1), ('A4', 1)],
    8: [('D5', .5), ('F5', .5), ('A5', 1), ('G5', .5), ('F5', .5), ('E5', 1)],
    9: [('E5', 1), ('D5', .5), ('C5', .5), ('B4', 1), ('G#4', 1)],
    10: [('C5', 1), ('F5', 1), ('A5', 2)],
    11: [('G5', 1.5), ('E5', .5), ('C5', 2)],
    12: [('D5', 1), ('F5', 1), ('A5', 1), ('C6', 1)],
    13: [('D6', 1), ('C6', 1), ('B5', 2)],
    14: [('E5', 1), ('G5', 1), ('C6', 2)],
    15: [('B5', 1), ('A5', 1), ('E5', 2)],
    16: [('A5', 1), ('G5', 1), ('F5', 1), ('E5', 1)],
    17: [('D5', 2), ('G5', 2)],
    18: [('A5', 2), ('G5', 2)],
    19: [('E5', 4)],
}


class Song:
    def __init__(self, seed):
        self.ev = []
        self.rng = random.Random(seed)

    def setup(self, ch, program, vol=100, pan=64, reverb=50, chorus=0):
        self.ev += [(0, 0, mido.Message('program_change', channel=ch, program=program)),
                    (0, 0, mido.Message('control_change', channel=ch, control=7, value=vol)),
                    (0, 0, mido.Message('control_change', channel=ch, control=10, value=pan)),
                    (0, 0, mido.Message('control_change', channel=ch, control=91, value=reverb)),
                    (0, 0, mido.Message('control_change', channel=ch, control=93, value=chorus))]

    def note(self, ch, t, pitch, dur, vel, human=0.012):
        t = max(0.0, t + self.rng.gauss(0, human))
        vel = int(max(1, min(127, vel + self.rng.randint(-6, 6))))
        self.ev.append((t, 1, mido.Message('note_on', channel=ch, note=pitch, velocity=vel)))
        self.ev.append((t + max(0.05, dur), 0, mido.Message('note_off', channel=ch, note=pitch, velocity=0)))

    def cc(self, ch, t, num, val):
        self.ev.append((t, 0, mido.Message('control_change', channel=ch, control=num, value=val)))

    def strum(self, ch, t, notes, dur, vel, up=False, gap=0.022):
        order = notes[::-1] if up else notes
        for i, p in enumerate(order):
            self.note(ch, t + i * gap, p, dur, vel - (i * 3 if up else 0), human=0.006)

    def melody(self, ch, bar, vel, octave=0, legato=0.95, swing=0.0, shift=0.0):
        t = bar * 4 + shift
        for name, d in MELODY[bar]:
            if name:
                tt = t + (swing if (t % 1) > 0.25 else 0)
                self.note(ch, tt, n(name) + 12 * octave, d * legato, vel)
            t += d

    def save(self, path):
        mid = mido.MidiFile(ticks_per_beat=TPB)
        tr = mido.MidiTrack()
        mid.tracks.append(tr)
        tr.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(BPM)))
        last = 0
        for t, _, msg in sorted(self.ev, key=lambda e: (e[0], e[1])):
            tick = int(round(t * TPB))
            tr.append(msg.copy(time=tick - last))
            last = tick
        mid.save(path)


# --------------------------------------------------------------------------
# 1 · piano íntimo
# --------------------------------------------------------------------------

PIANO = {
    'Cmaj7': (36, [48, 55, 59, 64]), 'Am7': (33, [45, 52, 55, 60]), 'Fmaj7': (41, [53, 57, 60, 64]),
    'Em7': (40, [52, 55, 59, 62]), 'Dm7': (38, [50, 53, 57, 60]), 'Am': (33, [45, 52, 57, 60]),
    'F': (41, [53, 57, 60, 65]), 'Dm': (38, [50, 53, 57, 62]), 'E7': (40, [52, 56, 59, 62]),
    'C/E': (40, [52, 55, 60, 64]), 'G': (43, [50, 55, 59, 62]), 'C': (36, [48, 55, 60, 64]),
    'Cadd9': (36, [48, 55, 62, 64]),
}


def piano():
    s = Song(1)
    s.setup(0, 0, vol=110, reverb=70)
    for bar, ch in enumerate(FORM):
        t0 = bar * 4
        sec = section(bar)
        bass, arp = PIANO[ch]
        # sustain pedal, changed on every bar (every beat when it gets tense)
        if sec == 'agresiva':
            for b in range(4):
                s.cc(0, t0 + b + 0.03, 64, 0)
                s.cc(0, t0 + b + 0.08, 64, 100)
        else:
            s.cc(0, t0 + 0.02, 64, 0)
            s.cc(0, t0 + 0.07, 64, 110)
        if sec == 'cierre' and bar == 19:
            s.note(0, t0, bass, 6, 52)
            for i, p in enumerate([48, 55, 62, 64, 67, 72]):
                s.note(0, t0 + 0.12 + i * 0.09, p, 6, 46 + i * 2, human=0.004)
            s.note(0, t0 + 0.9, n('E5'), 5, 58)
            s.note(0, t0 + 1.4, n('G5'), 4.5, 50)
            continue
        if sec == 'pasiva':
            s.note(0, t0, bass, 4, 44)
            for k, i in enumerate([0, 2, 3]):
                s.note(0, t0 + 1 + k, arp[i], 1.5, 36)
        elif sec == 'agresiva':
            s.note(0, t0, bass, 2, 58)
            s.note(0, t0, bass + 12, 2, 50)
            s.note(0, t0 + 2, bass, 2, 52)
            for k in range(8):
                acc = 54 if k % 2 == 0 else 44
                for p in arp[1:]:
                    s.note(0, t0 + k * 0.5, p, 0.42, acc - 8, human=0.006)
        else:
            v = {'intro': 46, 'asertiva': 58, 'formula': 50, 'cierre': 44}[sec]
            s.note(0, t0, bass, 4, v + 6)
            for k, i in enumerate([0, 1, 2, 3, 2, 1, 2]):
                s.note(0, t0 + 0.5 * (k + 1), arp[i], 1.2, v - (4 if k % 2 else 0))
        mv = {'intro': 58, 'pasiva': 50, 'agresiva': 64, 'asertiva': 76, 'formula': 64, 'cierre': 56}[sec]
        s.melody(0, bar, mv)
    s.cc(0, 80, 64, 0)
    return s


# --------------------------------------------------------------------------
# 2 · ukelele y silbido
# --------------------------------------------------------------------------

UKE = {  # re-entrant ukulele shapes (G C E A strings)
    'Cmaj7': [67, 60, 64, 71], 'Am7': [67, 60, 64, 69], 'Fmaj7': [69, 60, 64, 69], 'Em7': [67, 62, 64, 71],
    'Dm7': [69, 62, 65, 72], 'Am': [69, 60, 64, 69], 'F': [69, 60, 65, 69], 'Dm': [69, 62, 65, 69],
    'E7': [68, 62, 64, 71], 'C/E': [67, 60, 64, 72], 'G': [67, 62, 67, 71], 'C': [67, 60, 64, 72],
    'Cadd9': [67, 62, 64, 72],
}
ROOT = {'Cmaj7': 36, 'Am7': 33, 'Fmaj7': 41, 'Em7': 40, 'Dm7': 38, 'Am': 33, 'F': 41, 'Dm': 38, 'E7': 40,
        'C/E': 40, 'G': 43, 'C': 36, 'Cadd9': 36}


def ukelele():
    s = Song(2)
    s.setup(0, 24, vol=112, pan=48, reverb=45)      # nylon guitar, played high like a uke
    s.setup(1, 32, vol=100, pan=64, reverb=20)      # acoustic bass
    s.setup(2, 78, vol=92, pan=84, reverb=60)       # whistle
    s.setup(3, 9, vol=70, pan=76, reverb=70)        # glockenspiel
    s.setup(9, 0, vol=90, pan=70, reverb=30)        # percussion
    for bar, ch in enumerate(FORM):
        t0 = bar * 4
        sec = section(bar)
        v = UKE[ch]
        r = ROOT[ch]
        if bar == 19:
            s.strum(0, t0, v, 6, 70, gap=0.06)
            s.note(1, t0, r, 5, 70)
            s.note(2, t0 + 0.5, n('E5'), 3, 64)
            s.note(3, t0 + 0.5, n('C6'), 3, 50)
            continue
        if sec == 'pasiva':
            s.strum(0, t0, v, 2, 58, gap=0.04)
            s.strum(0, t0 + 2, v, 2, 50, gap=0.04)
            s.note(1, t0, r, 3.8, 62)
        elif sec == 'agresiva':
            for pos, kind in [(0, 'D'), (1, 'x'), (1.5, 'U'), (2, 'D'), (3, 'x'), (3.5, 'U')]:  # choppy
                if kind == 'x':      # muted "chuck"
                    s.strum(0, t0 + pos, v, 0.07, 72, gap=0.01)
                else:
                    s.strum(0, t0 + pos, v, 0.35, 64 if kind == 'D' else 50, up=kind == 'U', gap=0.018)
            s.note(1, t0, r, 0.9, 80)
            s.note(1, t0 + 1.5, r, 0.4, 66)
            s.note(1, t0 + 2, r + 7 if r + 7 < 48 else r, 0.9, 72)
            for k in range(8):
                s.note(9, t0 + k * 0.5, 69, 0.1, 44 if k % 2 == 0 else 30)       # cabasa
        else:
            vel = {'intro': 60, 'asertiva': 70, 'formula': 64, 'cierre': 58}[sec]
            pat = [(0, False), (1, False), (1.5, True), (2.5, True), (3, False), (3.5, True)]
            for k, (pos, up) in enumerate(pat):
                nxt = pat[k + 1][0] if k + 1 < len(pat) else 4
                s.strum(0, t0 + pos, v, nxt - pos - 0.03, vel if not up else vel - 14, up=up)
            s.note(1, t0, r, 1.4, 74)
            s.note(1, t0 + 2, r + 7 if r + 7 < 48 else r - 5, 1.2, 64)
            if sec != 'cierre':
                for k in range(8):
                    s.note(9, t0 + k * 0.5 + (0.04 if k % 2 else 0), 70, 0.1, 40 if k % 2 == 0 else 28)
        if sec in ('intro', 'asertiva', 'formula', 'cierre'):
            wv = {'intro': 70, 'asertiva': 84, 'formula': 76, 'cierre': 70}[sec]
            s.melody(2, bar, wv, octave=0, legato=0.85, swing=0.04)
        if sec == 'formula':
            s.melody(3, bar, 46, octave=1, legato=0.6)
    return s


# --------------------------------------------------------------------------
# 3 · lo-fi tranquilo
# --------------------------------------------------------------------------

LOFI_FORM = ['Cmaj9', 'Am9', 'Fmaj9', 'Em9', 'Dm9', 'Em7', 'Am9', 'Fmaj7#11', 'Dm9', 'E7b9',
             'Fmaj9', 'C/E', 'Dm9', 'G13', 'Cmaj9', 'Am9', 'Fmaj9', 'G9sus', 'Fmaj9', 'Cmaj9']
RHODES = {
    'Cmaj9': (36, [52, 55, 59, 62]), 'Am9': (33, [55, 59, 60, 64]), 'Fmaj9': (29, [57, 60, 64, 67]),
    'Em9': (40, [55, 59, 62, 66]), 'Dm9': (38, [53, 57, 60, 64]), 'Em7': (40, [52, 55, 59, 62]),
    'Fmaj7#11': (29, [53, 57, 59, 64]), 'E7b9': (40, [56, 59, 62, 65]), 'C/E': (40, [52, 55, 60, 64]),
    'G13': (31, [53, 57, 59, 64]), 'G9sus': (31, [53, 57, 60, 62]),
}
SW = 0.08  # swing on the off-beats


def lofi():
    s = Song(3)
    s.setup(0, 4, vol=108, pan=58, reverb=55, chorus=40)   # electric piano
    s.setup(1, 33, vol=104, pan=64, reverb=10)             # finger bass
    s.setup(2, 11, vol=80, pan=80, reverb=70)              # vibraphone
    s.setup(9, 0, vol=96, pan=64, reverb=25)               # drums
    for bar, ch in enumerate(LOFI_FORM):
        t0 = bar * 4
        sec = section(bar)
        root, v = RHODES[ch]
        if bar == 19:
            s.strum(0, t0, v + [67], 7, 54, gap=0.05)
        elif sec in ('intro', 'pasiva', 'cierre'):
            s.strum(0, t0, v, 3.8, 56 if sec != 'pasiva' else 50, gap=0.03)
        else:
            s.strum(0, t0, v, 1.3, 62, gap=0.02)
            s.strum(0, t0 + 2.5 + SW, v, 1.2, 54, gap=0.02)
        if sec != 'intro':
            s.note(1, t0, root, 1.6 if sec != 'cierre' else 3.8, 84)
            if sec not in ('pasiva', 'cierre'):
                s.note(1, t0 + 2.5 + SW, root + 12 if root < 36 else root, 0.8, 70)
                s.note(1, t0 + 3.5 + SW, root + 7 if root < 36 else root - 5, 0.4, 60)
        # drums
        if sec in ('pasiva', 'agresiva', 'asertiva', 'formula'):
            soft = sec == 'pasiva'
            s.note(9, t0, 36, 0.2, 70 if soft else 88)
            if not soft:
                s.note(9, t0 + 2.5 + SW, 36, 0.2, 74)
                if sec == 'agresiva':
                    s.note(9, t0 + 1.5 + SW, 36, 0.2, 62)
            for b in (1, 3):
                s.note(9, t0 + b, 37 if soft else 38, 0.2, 58 if soft else 62)
            for k in range(8):
                off = SW if k % 2 else 0
                s.note(9, t0 + k * 0.5 + off, 42, 0.1, (40 if k % 2 == 0 else 28) - (8 if soft else 0))
            if bar % 2 == 1 and not soft:
                s.note(9, t0 + 3.5 + SW, 46, 0.3, 34)
        if sec in ('asertiva', 'formula', 'cierre'):
            s.melody(2, bar, 64 if sec != 'cierre' else 56, octave=0, legato=0.9, swing=SW)
    return s


# --------------------------------------------------------------------------
# render + light mastering
# --------------------------------------------------------------------------

def lp(x, fc, order=2):
    b, a = butter(order, fc / (SR / 2))
    return lfilter(b, a, x, axis=0)


def hp(x, fc, order=1):
    b, a = butter(order, fc / (SR / 2), 'high')
    return lfilter(b, a, x, axis=0)


def render(song, name, lofi_fx=False):
    mid = os.path.join(TMP, name + '.mid')
    wav = os.path.join(TMP, name + '.wav')
    song.save(mid)
    subprocess.run(['fluidsynth', '-ni', '-q', '-g', '0.6', '-r', str(SR), '-F', wav, SF2, mid], check=True)
    sr, x = wavfile.read(wav)
    x = x.astype(np.float64) / 32768
    n_ = int(DUR * SR)
    if len(x) < n_:
        x = np.vstack([x, np.zeros((n_ - len(x), 2))])
    x = x[:n_]
    if lofi_fx:
        rng = np.random.default_rng(9)
        x = lp(x, 6500)
        x = np.tanh(1.6 * x) / 1.6
        hiss = lp(rng.normal(0, 1, (n_, 2)), 5000) * 0.004
        crackle = np.zeros((n_, 2))
        idx = rng.choice(n_, int(DUR * 7), replace=False)
        crackle[idx, rng.integers(0, 2, len(idx))] = rng.uniform(-1, 1, len(idx)) * 0.12
        crackle = hp(crackle, 1500)
        x = x + hiss + crackle
    x = hp(x, 30)
    fade = np.ones(n_)
    fade[-int(1.6 * SR):] = np.linspace(1, 0, int(1.6 * SR)) ** 1.6
    x *= fade[:, None]
    x /= np.abs(x).max() + 1e-9
    wavfile.write(wav, SR, (x * 0.9 * 32767).astype(np.int16))
    os.makedirs(OUT, exist_ok=True)
    mp3 = os.path.join(OUT, name + '.mp3')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', wav, '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11', '-ar', str(SR),
                    '-c:a', 'libmp3lame', '-b:a', '192k', mp3], check=True)
    return mp3


if __name__ == '__main__':
    print(render(piano(), 'opcion_1_piano_intimo'))
    print(render(ukelele(), 'opcion_2_ukelele_y_silbido'))
    print(render(lofi(), 'opcion_3_lofi_tranquilo', lofi_fx=True))

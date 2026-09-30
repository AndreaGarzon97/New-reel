"""Plays the reel's existing choreography (written for the round characters) with the
improved colored-pencil people: maps each Char state to an equivalent human pose."""
import math
import os

import numpy as np

import alt_chars as ac
from draw import hseed
from people import VERSIONS, person2

LOOK = VERSIONS[os.environ.get('REEL_PEOPLE', 'v1')]
EGG_S = 1.1 * 1.12   # default size of the round characters
PS0 = 1.02           # a person at that size
ARM = {'rest': 'rest', 'hug': 'crossed', 'shy': 'shy', 'open': 'open', 'point': 'point', 'fist': 'clench',
       'guard': 'guard', 'chest': 'chest', 'wave': 'wave', 'up': 'guard', 'hips': 'rest'}


def mood_of(c):
    if c.eyes == 'wide':
        return 'scared'
    if c.brow is not None and c.brow < -0.3:
        return 'angry'
    if c.eyes in ('happy', 'closed'):
        return 'talk' if c.mouth_open > 0.1 else 'happy'
    if (c.brow is not None and c.brow > 0.5) or c.wavy > 0.5:
        return 'sad'
    if c.mouth_open > 0.1:
        return 'calm'
    return 'smile' if c.mouth >= 0.3 else 'neutral'


def draw(ctx, c, key):
    ps = c.s / EGG_S * PS0 * (1.3 if c.sit else 1.0)
    cfg = LOOK['boy'] if c.name == 'A' else LOOK['girl']
    X = c.x
    if c.shake:
        r = np.random.default_rng(hseed(key, 'shake', int(ctx.t * 15)))
        X += (r.random() - 0.5) * 2 * c.shake
    arms, hands_to = [], []
    for spec in c.arms:
        if isinstance(spec, tuple) and spec[0] == 'abs':
            arms.append('rest')
            hands_to.append((spec[1], c.y - (40 if c.sit else 150) * ps))
        else:
            arms.append(ARM.get(spec, 'rest'))
            hands_to.append(None)
    shrink = float(np.clip((1 - c.squash) / 0.08, 0, 1))
    head = person2(ctx, X, c.y, ps, cfg, mood_of(c), key, arms=tuple(arms), lean=c.lean, look=c.look,
                   hands_to=tuple(hands_to), shrink=shrink, sit=c.sit, walk=c.walk, head_dy=c.bob * 0.8,
                   mopen=c.mouth_open, swing=c.legs_swing)
    if c.sweat > 0.01:
        ac.sweat(ctx, head + np.array([66.0, -34.0]) * ps, ps * c.sweat, (key, 'sw'))
    if c.anger > 0.01:
        ac.anger_marks(ctx, head + np.array([-64.0, -70.0]) * ps, ps * c.anger, (key, 'am'))
    return {'head_top': head}

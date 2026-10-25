"""Rick's own attacks: Splatterhouse's moves in place of Marduk's animations, in Rick's motion pack (RIC2).

Each entry of ATTACKS replaces one of Marduk's body animations (its index in his motion pack; his moves play it as
0x4000 + index) with a Splatterhouse animation retargeted as his stance is (ttt2rick.convert.idle.Retarget). The
moves themselves stay Marduk's (damage, hitbox, active frames, recovery), so each animation is retimed onto his:
the Splatterhouse frame where the striking hand is furthest out (`peak`) lands on the move's first active frame,
the frames before it spread evenly over the frames before that, the rest over the remainder of Marduk's length.
Every attack takes out the stance's root turn (they all end in his stance: root -40, chest -13 degrees in Havok's
terms) and blends in from the stance's pose over BLEND_IN frames, as Splatterhouse blends out of its idle: his
stance has the right side forward, and its left punches start wound the other way (hips +24..+55 degrees).

The X button's chain in Splatterhouse (statemachines/player_initialrick/playercomboattackstates.smf: Idle ->
AttackPunchLeft -> AttackPunchRight -> ...) starts with a left then a right haymaker, which lunge far more than a jab:
they are his b+1 and b+1,2 (Marduk's Va_lp00B, and Va_ttlprp, which its 2 cancels into within frames 1-22), whose
first active frames (21, 32) give the left one about Splatterhouse's own speed. His 1 and 1,2 stay Marduk's.
"""
import os

import numpy as np

from ..splatterhouse import hkx

BLEND_IN = 6                     # frames at 60 fps from the stance's pose into an attack
# Marduk's body animation -> (Splatterhouse animation, its frame of full extension at 30 fps, Marduk's move that
# plays it, the move's first active frame at 60 fps)
ATTACKS = {
    0xDD: ('atk_punchl_high.hkx', 10, 'Va_lp00B', 21),    # b+1: AttackPunchLeftHigh, L_weapon_jnt (80 frames)
    0xDE: ('atk_punchr_high.hkx', 10, 'Va_ttlprp', 32),   # b+1,2: AttackPunchRightHigh, R_weapon_jnt (85 frames)
}


def retime(frames_src, peak, frames_dst, impact):
    """Havok frame numbers for each of frames_dst output frames: 0..peak over 0..impact, peak..end over the rest."""
    k = np.arange(frames_dst, dtype=float)
    before = k * peak / impact
    after = peak + (k - impact) * (frames_src - 1 - peak) / max(1, frames_dst - 1 - impact)
    return np.where(k <= impact, before, after)


def with_attacks(pack, retarget, lengths, stance):
    """The motion pack with every ATTACKS animation replaced (lengths: Marduk's frame count of each index; stance:
    the stance's Havok animation, already retargeted), and a {index: (Havok joints, TTT2 joints) per frame}."""
    from .idle import FPS, sample, with_animation
    start = sample(hkx.animation(hkx.Packfile(open(os.path.join(retarget.folder, stance), 'rb').read())),
                   retarget.sk, FPS)[0]
    shown = {}
    for index, (name, peak, move, impact) in ATTACKS.items():
        an = hkx.animation(hkx.Packfile(open(os.path.join(retarget.folder, name), 'rb').read()))
        times = retime(an['frames'], peak, lengths[index], impact)
        anim, hp, tp = retarget(name, times=times, yaw=retarget.yaws[stance], blend_from=(start, BLEND_IN))
        pack = with_animation(pack, index, anim)
        shown[index] = (hp, tp)
        print('%s -> body animation %#x (%s): %d frames, its frame %d at frame %d' % (
            name, index, move, len(times), peak, impact))
    return pack, shown

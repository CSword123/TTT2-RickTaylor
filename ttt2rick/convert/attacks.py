"""Rick's own attacks: Splatterhouse's moves in place of Marduk's animations, in Rick's motion pack (RIC2), and the
moveset changes they need (edit_moveset, applied by ttt2rick.convert.slot to RIC1).

Each entry of ATTACKS replaces one of Marduk's body animations (its index in his motion pack; his moves play it as
0x4000 + index) with a Splatterhouse animation retargeted as his stance is (ttt2rick.convert.idle.Retarget); each
of NEW_ATTACKS is appended to the pack for a move of Rick's own (NEW_MOVES). The moves' damage, hitbox, active
frames and recovery are Marduk's (or the move they copy), so each animation is retimed onto them: the Splatterhouse
frame where the striking hand is furthest out (`peak`) lands on the move's first active frame, the frames before
it spread evenly over the frames before that, the rest over the remaining length.
Every attack takes out the stance's root turn (they all end in his stance: root -40, chest -13 degrees in Havok's
terms) and blends in from the stance's pose over BLEND_IN frames, as Splatterhouse blends out of its idle: his
stance has the right side forward, and its left punches start wound the other way (hips +24..+55 degrees).
Splatterhouse's root motion is turned in place, so each attack carries him FORWARD (ground displacement, channel 0)
from the end of the blend to just after the hit, eased.

The X button's chain in Splatterhouse (statemachines/player_initialrick/playercomboattackstates.smf: Idle ->
AttackPunchLeft -> AttackPunchRight -> ...) starts with a left then a right haymaker, which lunge far more than a jab:
they are his b+1 and b+1,2 (Marduk's Va_lp00B, and Va_ttlprp, which its 2 cancels into), whose first active frames
(21, 32) give the left one about Splatterhouse's own speed; the chain's 360Punch (atk_punch_360, left arm) is his
b+1,1, a move of his own copied from Va_ttlprp. His 1 and 1,2 stay Marduk's. The second swings come out only once
the first has swung through (FOLLOW_UP_FRAME; Marduk's 2 came out at frame 22, right after b+1's hit).
"""
import os

import numpy as np

from ..splatterhouse import hkx

BLEND_IN = 6                     # frames at 60 fps from the stance's pose into an attack
FORWARD = 400.0                  # ground displacement units (Marduk's dash: 1429; his own b+1: 1813)
FOLLOW_UP_FRAME = 44             # b+1's frame from which its second swing comes out (its left swing back: Havok 22)
# Marduk's body animation -> (Splatterhouse animation, its frame of full extension at 30 fps, Marduk's move that
# plays it, the move's first active frame at 60 fps)
ATTACKS = {
    0xDD: ('atk_punchl_high.hkx', 10, 'Va_lp00B', 21),    # b+1: AttackPunchLeftHigh, L_weapon_jnt (80 frames)
    0xDE: ('atk_punchr_high.hkx', 10, 'Va_ttlprp', 32),   # b+1,2: AttackPunchRightHigh, R_weapon_jnt (85 frames)
}
# appended body animations, in order from SPIN_ANIM: (Splatterhouse animation, peak, frames, first active frame)
SPIN_ANIM = 685                  # after the guard (ttt2rick.convert.idle GUARD_ANIM 684)
NEW_ATTACKS = [('atk_punch_360.hkx', 14, 85, 32)]       # b+1,1: 360Punch, L_weapon_jnt (Havok peak 14)
# Rick's own moves: (name, the move copied, its body animation, hitbox from, after move, button)
LEFT_ARM = 'Va_lp00B'            # hitbox 0d0c: left hand and forearm (right: 0908)
NEW_MOVES = [('Va_ttlplp_ric', 'Va_ttlprp', SPIN_ANIM, LEFT_ARM, 'Va_lp00B', 0x40000001)]
DELAYED = [('Va_lp00B', 'Va_ttlprp')]                   # cancels that wait for FOLLOW_UP_FRAME


def retime(frames_src, peak, frames_dst, impact):
    """Havok frame numbers for each of frames_dst output frames: 0..peak over 0..impact, peak..end over the rest."""
    k = np.arange(frames_dst, dtype=float)
    before = k * peak / impact
    after = peak + (k - impact) * (frames_src - 1 - peak) / max(1, frames_dst - 1 - impact)
    return np.where(k <= impact, before, after)


def travel(frames, impact):
    """(frames, 3) ground displacement: FORWARD along z, eased from BLEND_IN to a few frames after the hit."""
    k = np.arange(frames, dtype=float)
    u = np.clip((k - BLEND_IN) / max(1, impact + 4 - BLEND_IN), 0, 1)
    out = np.zeros((frames, 3))
    out[:, 2] = FORWARD * u * u * (3 - 2 * u)
    return out


def _attack(retarget, start, name, peak, frames, impact, stance):
    an = hkx.animation(hkx.Packfile(open(os.path.join(retarget.folder, name), 'rb').read()))
    times = retime(an['frames'], peak, frames, impact)
    return retarget(name, times=times, yaw=retarget.yaws[stance], blend_from=(start, BLEND_IN),
                    ground=travel(frames, impact))


def _stance_pose(retarget, stance):
    from .idle import FPS, sample
    return sample(hkx.animation(hkx.Packfile(open(os.path.join(retarget.folder, stance), 'rb').read())),
                  retarget.sk, FPS)[0]


def with_attacks(pack, retarget, lengths, stance):
    """The motion pack with every ATTACKS animation replaced (lengths: Marduk's frame count of each index; stance:
    the stance's Havok animation, already retargeted), and a {index: (Havok joints, TTT2 joints) per frame}."""
    from .idle import with_animation
    start = _stance_pose(retarget, stance)
    shown = {}
    for index, (name, peak, move, impact) in ATTACKS.items():
        anim, hp, tp = _attack(retarget, start, name, peak, lengths[index], impact, stance)
        pack = with_animation(pack, index, anim)
        shown[index] = (hp, tp)
        print('%s -> body animation %#x (%s): %d frames, its frame %d at frame %d' % (
            name, index, move, lengths[index], peak, impact))
    return pack, shown


def with_new_attacks(pack, retarget, stance):
    """The motion pack with NEW_ATTACKS appended from SPIN_ANIM on, and their previews."""
    from .idle import with_appended
    start = _stance_pose(retarget, stance)
    shown = {}
    for k, (name, peak, frames, impact) in enumerate(NEW_ATTACKS):
        anim, hp, tp = _attack(retarget, start, name, peak, frames, impact, stance)
        pack, index = with_appended(pack, anim)
        if index != SPIN_ANIM + k:
            raise ValueError('%s went to body animation %d, not %d' % (name, index, SPIN_ANIM + k))
        shown[index] = (hp, tp)
        print('%s -> new body animation %d (%#x): %d frames, its frame %d at frame %d' % (
            name, index, 0x4000 + index, frames, peak, impact))
    return pack, shown


def edit_moveset(m):
    """Rick's moveset (a motbin.read of RIC1, its other changes made) rebuilt with NEW_MOVES and DELAYED: each new
    move appended (a copy, its own name, body animation and hitbox), and each move that gets a new follow-up given a
    copy of its cancel list at the end of the table with the follow-up next to the move it was copied from, so no
    index moves."""
    from ..ttt2.petexy import motbin
    moves, cancels = m.tables['moves'], m.tables['cancels']
    names = [m.move_name(i) for i in range(len(moves))]
    header, strings, mota_blob, mota_slots = motbin.split(m)
    strings = bytearray(strings)

    def cancel_list(i):
        return [r for _, r in m.iter_list('cancels', moves[i]['cancel'], lambda r: r['direction'] == 0x8000)]
    for src, dst in DELAYED:
        for r in cancel_list(names.index(src)):
            if r['move_id'] == names.index(dst):
                r['win_end'] = r['start_frame'] = FOLLOW_UP_FRAME
    for name, copy, anim, hitbox_from, after, button in NEW_MOVES:
        move = dict(moves[names.index(copy)])
        move['name'] = len(strings)
        strings += name.encode('latin1') + b'\0'
        move['anim'] = 0x4000 + anim
        move['hitbox'] = moves[names.index(hitbox_from)]['hitbox']
        moves.append(move)
        i = names.index(after)
        rows = [dict(r) for r in cancel_list(i)]
        like = next(r for r in rows if r['move_id'] == names.index(copy))
        rows.insert(rows.index(like), dict(like, button=button, move_id=len(moves) - 1))
        moves[i]['cancel'] = len(cancels)
        cancels.extend(rows)
        print('%s (move %d, body animation %d) after %s on button %#x, from frame %d' % (
            name, len(moves) - 1, anim, after, button, like['start_frame']))
    return motbin.build(header, bytes(strings), m.tables, mota_blob, mota_slots)

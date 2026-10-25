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
Splatterhouse's root motion is turned in place, so each attack carries him forward (its `forward`: ground
displacement, channel 0) from the end of the blend to just after the hit, eased. Splatterhouse turns him toward his
target as he punches, and its right punch and spin are thrown off his facing (48 and 29 degrees): in TTT2, where
hitboxes are on the bones, they missed anything not pinned to a wall. So each attack is also turned (aim) until the
striking hand points straight ahead on its first active frame, the turn eased in over the windup and out again over
the recovery, so it still starts and ends in his stance.

The X button's chain in Splatterhouse (statemachines/player_initialrick/playercomboattackstates.smf: Idle ->
AttackPunchLeft -> AttackPunchRight -> ...) starts with a left then a right haymaker, which lunge far more than a jab:
they are his b+1 and b+1,2 (Marduk's Va_lp00B, and Va_ttlprp, which its 2 cancels into); the chain's 360Punch
(atk_punch_360, left arm) is his b+1,1, a move of his own copied from Va_ttlprp. His 1 and 1,2 stay Marduk's.

Timing (STARTUP; edit_moveset moves each move's active frames, end and frame-keyed extra properties by the same
amount, so only the startup changes): b+1 is i16, the left haymaker's own speed in Splatterhouse (Marduk's: i21;
Splatterhouse's hit volume is on from about i4, the fist out at 16). Its second swings come out at FOLLOW_UP_FRAME,
once the left one has mostly swung back (Marduk's came out at 22, right after the hit), and are i20 (the right
haymaker's own windup; the spin's sped up 1.4x): they hit 32 frames after b+1 does.

Hit reactions (REACTIONS): Marduk's b+1 and b+1,2 leave the opponent crouched (sDm_KAKLcrG, 43 frames, ending in
the crouch), under the high follow-ups. b+1 and b+1,2 now snap the head back standing (sDm_Lhd00G / sDm_Rhd40GY,
left and right, 40 frames, standing on counter hit too, no pushback), so the follow-ups combo on hit with 8 frames
to spare; the heavy crouching crumple is b+1,1's finisher (copied from Va_ttlprp before the change).
"""
import os

import numpy as np

from ..splatterhouse import hkx

BLEND_IN = 6                     # frames at 60 fps from the stance's pose into an attack
# forward travel (ground displacement units): Marduk's dash 1429, his own b+1 1813 and b+1,2 2080
FIRST, FOLLOW_UP = 700.0, 900.0
FOLLOW_UP_FRAME = 28             # b+1's frame from which its second swings come out (Marduk's: 22)
# first and last active frames (Marduk's: 21-22, 32-32): the follow-ups' fists sweep through, out furthest only on
# frame 20 (1534 units, 1166 on 19, 1432 on 21), so they stay out through 22 or a b+1 landed from further off whiffs
STARTUP = {'Va_lp00B': (16, 17), 'Va_ttlprp': (20, 22)}
# Marduk's body animation -> (Splatterhouse animation, its frame of full extension at 30 fps, Marduk's move that
# plays it, its first active frame at 60 fps, frames: Marduk's less the startup taken off; the striking hand, the
# forward travel)
ATTACKS = {
    0xDD: ('atk_punchl_high.hkx', 10, 'Va_lp00B', 16, 75, 'L', FIRST),       # b+1: AttackPunchLeftHigh (80)
    0xDE: ('atk_punchr_high.hkx', 10, 'Va_ttlprp', 20, 73, 'R', FOLLOW_UP),  # b+1,2: AttackPunchRightHigh (85)
}
# appended body animations, in order from SPIN_ANIM: (Splatterhouse animation, peak, frames, first active frame,
# the striking hand, the forward travel)
SPIN_ANIM = 685                  # after the guard (ttt2rick.convert.idle GUARD_ANIM 684)
NEW_ATTACKS = [('atk_punch_360.hkx', 14, 73, 20, 'L', FOLLOW_UP)]   # b+1,1: 360Punch (Havok peak 14)
# Rick's own moves: (name, the move copied, its body animation, hitbox from, after move, button)
LEFT_ARM = 'Va_lp00B'            # hitbox 0d0c: left hand and forearm (right: 0908)
NEW_MOVES = [('Va_ttlplp_ric', 'Va_ttlprp', SPIN_ANIM, LEFT_ARM, 'Va_lp00B', 0x40000001)]
DELAYED = [('Va_lp00B', 'Va_ttlprp')]                   # cancels that wait for FOLLOW_UP_FRAME
# move -> (its reaction to replace, the new one), by the reactions' normal-hit (default) moves
REACTIONS = {'Va_lp00B': ('sDm_KAKLcrG', 'sDm_Lhd00G'), 'Va_ttlprp': ('sDm_KAKLcrG', 'sDm_Rhd40GY')}


def retime(frames_src, peak, frames_dst, impact):
    """Havok frame numbers for each of frames_dst output frames: 0..peak over 0..impact, peak..end over the rest."""
    k = np.arange(frames_dst, dtype=float)
    before = k * peak / impact
    after = peak + (k - impact) * (frames_src - 1 - peak) / max(1, frames_dst - 1 - impact)
    return np.where(k <= impact, before, after)


def ease(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def travel(frames, impact, forward):
    """(frames, 3) ground displacement: `forward` along z, eased from BLEND_IN to a few frames after the hit."""
    k = np.arange(frames, dtype=float)
    out = np.zeros((frames, 3))
    out[:, 2] = forward * ease((k - BLEND_IN) / max(1, impact + 4 - BLEND_IN))
    return out


def aim(frames, impact):
    """0..1 per frame: how much of the aiming turn is on (in over the windup, held a few frames, out by the end)."""
    k = np.arange(frames, dtype=float)
    return np.where(k <= impact + 4, ease(k / (impact + 4)),
                    1 - ease((k - impact - 4) / max(1, frames - 1 - impact - 4)))


def _attack(retarget, start, name, peak, frames, impact, hand, forward, stance):
    """(raw animation, Havok joints, TTT2 joints) of an attack: retimed, turned to aim, carried forward."""
    an = hkx.animation(hkx.Packfile(open(os.path.join(retarget.folder, name), 'rb').read()))
    times = retime(an['frames'], peak, frames, impact)
    base = retarget.yaws[stance]
    kw = dict(times=times, blend_from=(start, BLEND_IN), ground=travel(frames, impact, forward))
    names = [n[4:] if n.startswith('cha:') else n for n in retarget.bon['names']]
    h = names.index('TE_%s_jnt' % hand)
    _, _, tp = retarget(name, yaw=base, **kw)
    x, _, z = tp[impact][h]
    off = np.arctan2(x, z)                          # the hand's direction from straight ahead (+z)
    out = retarget(name, yaw=base + off * aim(frames, impact), **kw)
    x, _, z = out[2][impact][h]
    print('%s: aimed %.0f degrees (the %s hand now %.0f off)' % (name, np.degrees(off), hand,
                                                                 np.degrees(np.arctan2(x, z))))
    return out


def _stance_pose(retarget, stance):
    from .idle import FPS, sample
    return sample(hkx.animation(hkx.Packfile(open(os.path.join(retarget.folder, stance), 'rb').read())),
                  retarget.sk, FPS)[0]


def with_attacks(pack, retarget, stance):
    """The motion pack with every ATTACKS animation replaced (stance: the stance's Havok animation, already
    retargeted), and a {index: (Havok joints, TTT2 joints) per frame}."""
    from .idle import with_animation
    start = _stance_pose(retarget, stance)
    shown = {}
    for index, (name, peak, move, impact, frames, hand, forward) in ATTACKS.items():
        anim, hp, tp = _attack(retarget, start, name, peak, frames, impact, hand, forward, stance)
        pack = with_animation(pack, index, anim)
        shown[index] = (hp, tp)
        print('%s -> body animation %#x (%s): %d frames, its frame %d at frame %d' % (
            name, index, move, frames, peak, impact))
    return pack, shown


def with_new_attacks(pack, retarget, stance):
    """The motion pack with NEW_ATTACKS appended from SPIN_ANIM on, and their previews."""
    from .idle import with_appended
    start = _stance_pose(retarget, stance)
    shown = {}
    for k, (name, peak, frames, impact, hand, forward) in enumerate(NEW_ATTACKS):
        anim, hp, tp = _attack(retarget, start, name, peak, frames, impact, hand, forward, stance)
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

    def own(i, field, table, end_test):
        """Move i's list in `table` (its rows, edited in place): a copy at the table's end when other moves share it."""
        if sum(1 for r in moves if r[field] == moves[i][field]) > 1:
            rows = [dict(r) for _, r in m.iter_list(table, moves[i][field], end_test)]
            moves[i][field] = len(m.tables[table])
            m.tables[table].extend(rows)
        return [r for _, r in m.iter_list(table, moves[i][field], end_test)]
    for name, (first, last) in STARTUP.items():
        i = names.index(name)
        d = moves[i]['first_active'] - first
        moves[i]['first_active'], moves[i]['last_active'] = first, last
        for r in own(i, 'cancel', 'cancels', lambda r: r['direction'] == 0x8000):
            if r['direction'] == 0x8000:                      # the move's end
                r['win_start'] -= d
                r['start_frame'] -= d
        for r in own(i, 'extraprops', 'extra_move_properties', lambda r: r['frame'] == 0 and r['id'] == 0):
            if r['frame']:
                r['frame'] = max(1, r['frame'] - d)
        print('%s: i%d (%d frames earlier, its end too)' % (name, first, d))
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
    # after NEW_MOVES: their copies keep the moves' old reactions
    reactions = m.tables['reactions']
    hit_end = lambda h: h['req'] is None or m.tables['requirements'][h['req']]['condition'] == 690   # no condition
    for name, (old, new) in REACTIONS.items():
        i = names.index(name)
        to = next(k for k, r in enumerate(reactions) if r['default'] is not None and r['default'] < len(names)
                  and names[r['default']] == new)
        for h in own(i, 'hit_condition', 'hit_conditions', hit_end):
            r = reactions[h['reactions']] if h['reactions'] is not None else None
            if r is not None and r['default'] is not None and r['default'] < len(names) and names[r['default']] == old:
                h['reactions'] = to
        print('%s: hit reaction %s -> %s (reactions %d)' % (name, old, new, to))
    return motbin.build(header, bytes(strings), m.tables, mota_blob, mota_slots)

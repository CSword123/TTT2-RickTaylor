"""Rick's u+1+2: Splatterhouse's grab (the B button), a throw that lifts the opponent over his head and tosses them
far forward, built on Marduk's front throw (1+3) and played in Rick's motion pack by with_grab (moves: attacks
NEW_MOVES, edit_moveset's GRAB rows).

In Splatterhouse (statemachines/player_initialrick/playergrabstates.smf) B is Atk_Grab, the reach (GrabMiss,
grabmiss.hkx at rate 1.2; a whiff plays it out); a catch goes on to Grab (GRB_grab_stand, grb_stand.hkx from its
frame 13, where the reach's hands close: he heaves the enemy up over his head by frame 28), then holds it there
(GrappleState, grb_idle.hkx) until B throws it (ThrowEnemy, GRB_Throw: grb_throw.hkx, both hands overhead, cocked
back by 24, flung forward by 30, recovered by 48). Here the lift goes straight on into the throw (the user's call,
2026-10-27): grb_stand's frame 28 is grb_throw's first pose.

A TTT2 throw is three moves of the thrower's: the attempt (Marduk's 1+3, ThrmvLB2_00: a common grab animation, a
throw hit at frames 12-14), whose cancels on a catch (requirement 1348 for a catch from the front) go on to the throw
itself (Va_nagef_n), whose hit makes the opponent play the thrower's victim move (Va_nagef_y, its reaction's
default), with an animation of the thrower's motion pack. The two animations are made to fit one frame of reference:
each one's ground displacement (channel 0) places its fighter, the thrower facing +z, the victim turned around (its
turn channel: half a turn), so Marduk's victim starts at his ground 0 and Marduk 883 mm behind it (checked on his
throw: his hands stay within a few cm of the victim's body through its lift, frames 0-50).

So Rick's throw (THROW) and its victim (the opponent, VICTIM) are made together:
- the attempt is Splatterhouse's reach (REACH), its hands' closing (Havok frame 12) on the attempt's throw hit;
- the throw plays grb_stand from frame 13 to LIFT_END, then grb_throw to THROW_END, at Splatterhouse's speed;
- the victim takes Marduk's victim's poses (his body and limbs, 0x166): his frames 0-50 (grabbed, heaved up over
  the thrower's head) over Rick's lift, frame 50 held through his wind-up, 50-100 (turning over and coming down on
  the back) over the flight, and 100 on lying there (the pose dwDWN_01D, where Va_nagef_y ends, starts from). Where
  Rick holds the victim, the victim is held as Marduk holds him: the point where Marduk's hands are, in the victim's
  hips' frame, stays at Rick's hands. From the release (grb_throw's frame RELEASE) he flies on a ballistic arc
  (TTT2's gravity: 1 G) over Rick's head to TOSS mm in front of him, and lands in FLIGHT frames, sliding SLIDE mm on.
- Rick's own steps carry him (footwork), set back so his hands close where Marduk's do on the victim (his arms are
  longer than Marduk's: his hands close 1.5 m in front of him). Until the victim leaves the floor he stands where
  Marduk's victim does (HELD_FROM), then Rick's hands carry him.
Marduk's throw's own timed properties (the damage at the slam, the opponent's fall and the ground's shake, the camera)
come along, moved to the same moments of Rick's (frame_map).
"""
import numpy as np

from . import attacks

GRAB_ANIM = attacks.GRAB_ANIM      # the attempt, the throw, the victim (704-706)
REACH = 'grabmiss.hkx'
REACH_PEAK = 12                    # Havok frame: the hands close in front of him (z 1540 mm)
REACH_IMPACT = 12                  # the attempt's throw hit (Marduk's 1+3: frames 12-14)
REACH_FRAMES = 52                  # a whiff plays the reach out (Marduk's: 39)
THROW = 'grb_stand.hkx+grb_throw.hkx'
STAND_FRAMES = 40                  # grb_stand's, before grb_throw's in THROW
LIFT_START, LIFT_END = 13.0, 28.0  # grb_stand: from the catch to the opponent over his head
THROW_END = 50.0                   # grb_throw: settled back in his stance
RELEASE = 29.0                     # grb_throw: the hands fling forward past his head (24 cocked back, 30 out front)
RATE = 2.0                         # TTT2 frames (60 fps) a Havok frame (30 fps): Splatterhouse's own speed
TOSS = 3800.0                      # mm in front of Rick that the opponent lands (Marduk's slam: 2.3 m in front of
                                   # him); let go cocked behind his head, the opponent flies over him to it
FLIGHT = 44                        # frames in the air
SLIDE, SLIDE_FRAMES = 350.0, 14    # mm the landing carries on, over frames
GRAVITY = 9810.0                   # mm / s^2
LIE = 50                           # frames lying after the landing (Marduk's victim: 80) before dwDWN_01D
END_HOLD = 8                       # frames Rick stands after his throw's recovery
# Marduk's front throw: his throw and its victim (body animations 0x165, 0x166; 180 frames each), and their frames:
# the lift's top (the victim over his head), the victim on the floor
DONOR = (0x165, 0x166)
DONOR_LIFT, DONOR_LAND, DONOR_END = 50, 100, 180
HANDS = ('TE_R_jnt', 'TE_L_jnt')
# Marduk's victim's frames over which Rick's hands take him over: before, he stands where Marduk's victim does
# (Rick's hands close lower than Marduk's: held by them from the catch, his feet sank 0.45 m into the floor), from
# the second on he is where Rick's hands hold him (Marduk's victim leaves the floor by 30)
HELD_FROM = (12.0, 34.0)


def timeline():
    """{'lift': frames of the lift, 'release': Rick's frame of the release, 'land': the victim's landing frame,
    'throw': Rick's throw's frames, 'victim': the victim's}."""
    lift = int(round((LIFT_END - LIFT_START) * RATE))
    release = lift + int(round(RELEASE * RATE))
    throw = lift + int(round(THROW_END * RATE)) + 1
    land = release + FLIGHT
    return dict(lift=lift, release=release, land=land, throw=throw + END_HOLD, victim=land + LIE)


def frame_map(frame):
    """A frame of Marduk's throw (or its victim's) -> the same moment of Rick's: the lift, the flight, the floor."""
    t = timeline()
    if frame >= 0x4000:                 # not a frame (0x8001: from the start)
        return frame
    if frame <= DONOR_LIFT:
        return max(1, int(round(frame * t['lift'] / DONOR_LIFT)))
    if frame <= DONOR_LAND:
        return t['release'] + int(round((frame - DONOR_LIFT) * FLIGHT / (DONOR_LAND - DONOR_LIFT)))
    return t['land'] + frame - DONOR_LAND


def _channels(values, typ):
    """(frames, 23, 3, 3) the body channels' rotations of a decoded animation (identity for the others)."""
    from ..ttt2.petexy import animation
    out = np.tile(np.eye(3), (len(values), 23, 1, 1))
    for c, d in enumerate(animation.BODY_DESCRIPTORS):
        if animation.is_rotation(d):
            for f in range(len(values)):
                out[f, c] = animation.local_rotation(np.asarray(values[f, c], np.float64), typ)
    return out


def _worlds(values, rots, bon):
    """(frames, bones, 3) world joint positions (mm, the shared frame) of a decoded animation on skeleton bon, and
    (frames, 3, 3) its hips' world rotation."""
    from ..ttt2 import fk
    bi = fk.bone_index(bon)
    sc = float(bon['scale'])
    pos, hips = [], []
    for f in range(len(values)):
        local = {bi[b]: rots[f, c] for c, b in fk.CHANNEL_BONES.items()}
        W = fk.world(bon, local, values[f, 1] * np.array([1, 1, -1]))
        T = rots[f, 2]
        pos.append(np.einsum('ij,nj->ni', T, W[:, :3, 3] * sc) + values[f, 0] * sc)
        hips.append(T @ W[0, :3, :3])
    return np.array(pos), np.array(hips)


def _blend(Ra, Rb, u):
    return attacks._turn_between(Ra, Rb, u)


def with_grab(pack, retarget, stance, arc):
    """The motion pack with the grab's three animations appended from GRAB_ANIM on: the attempt, the throw, the
    victim."""
    from .idle import MARDUK_MOTIONS, load_animation, mota, raw_animation, sample, with_appended
    from ..ttt2 import fk, xbox
    from ..ttt2.petexy import animation, bone
    start = attacks._stance_pose(retarget, stance)
    t = timeline()

    names = [n[4:] if n.startswith('cha:') else n for n in retarget.bon['names']]
    hands = [names.index(h) for h in HANDS]
    rscale = float(retarget.bon['scale'])
    base = retarget.yaws[stance]

    # the attempt: the reach, his hands meeting in front of him on its throw hit. Splatterhouse's grab clips face
    # their own way (not the stance's), so the reach is turned until the point between his hands is straight ahead
    # at the catch, the turn eased in over the reach and out over a whiff's recovery
    an = load_animation(retarget.folder, REACH, retarget.sk)
    times = attacks.retime(an['frames'], REACH_PEAK, REACH_FRAMES, REACH_IMPACT)
    kw = dict(times=times, blend_from=(start, attacks.BLEND_IN))
    _, _, tp = retarget(REACH, yaw=base, **kw)
    x, _, z = tp[REACH_IMPACT][hands].mean(0)
    off = np.arctan2(x, z)
    k = np.arange(REACH_FRAMES, dtype=float)
    hold = REACH_IMPACT + 6
    turn = np.where(k <= REACH_IMPACT, attacks.ease(k / REACH_IMPACT),
                    1 - attacks.ease((k - hold) / (REACH_FRAMES - 1 - hold)))
    _, _, tp = retarget(REACH, yaw=base + off * turn, **kw)
    kw['ground'] = attacks.footwork(tp, retarget.bon)
    reach, _, tp = retarget(REACH, yaw=base + off * turn, **kw)
    x, _, z = tp[REACH_IMPACT][hands].mean(0)
    print('grab: the reach turned %.0f degrees (its hands now %.0f off), %.0f mm forward by the catch' % (
        np.degrees(off), np.degrees(np.arctan2(x, z)), kw['ground'][REACH_IMPACT][2] * rscale))
    pack, at = with_appended(pack, reach)
    if at != GRAB_ANIM:
        raise ValueError('the grab\'s reach went to body animation %d, not %d' % (at, GRAB_ANIM))

    # the throw: the lift, then the toss, from the reach's pose at its throw hit, turned as the reach is at the
    # catch, the turn eased out over its recovery
    caught = sample(an, retarget.sk, 60.0, [times[REACH_IMPACT]])[0]
    times = np.concatenate([LIFT_START + np.arange(t['lift']) / RATE,
                            STAND_FRAMES + np.arange(t['throw'] - t['lift']) / RATE])
    times = np.minimum(times, STAND_FRAMES + THROW_END)
    k = np.arange(t['throw'], dtype=float)
    back = t['release'] + 8
    yaw = base + off * (1 - attacks.ease((k - back) / (t['throw'] - 1 - back)))
    kw = dict(times=times, yaw=yaw, blend_from=(caught, 4))
    _, _, tp = retarget(THROW, **kw)
    feet = attacks.footwork(tp, retarget.bon)
    held = np.array([p[hands].mean(0) for p in tp]) + feet * rscale     # his hands, his ground at 0

    # Marduk's throw and its victim, in their shared frame
    mpack = arc.read(MARDUK_MOTIONS)
    mbon = xbox.read_bone(arc.read_name('mar.bon'))
    mbi = fk.bone_index(mbon)
    o0, offsets = mota(mpack)
    donor = [animation.decode(mpack, '>', o0 + offsets[i]) for i in DONOR]
    drots = [_channels(d['values'], d['type']) for d in donor]
    mpos, _ = _worlds(donor[0]['values'], drots[0], mbon)
    vpos, vhips = _worlds(donor[1]['values'], drots[1], mbon)
    mhands = mpos[:, [mbi[h] for h in HANDS]].mean(1)
    grip = np.einsum('fji,fj->fi', vhips, mhands - vpos[:, 0])         # Marduk's hands in the victim's hips' frame
    vscale = float(mbon['scale'])
    vvalues = donor[1]['values']

    # the victim: Marduk's victim's poses (by its frame `src` at each of ours), his hips where Rick holds him, then
    # thrown
    n = t['victim']
    src = np.empty(n)
    k = np.arange(n, dtype=float)
    lift, release, land = t['lift'], t['release'], t['land']
    src[:lift + 1] = k[:lift + 1] * DONOR_LIFT / lift
    src[lift:release + 1] = DONOR_LIFT
    src[release:land + 1] = DONOR_LIFT + (k[release:land + 1] - release) * (DONOR_LAND - DONOR_LIFT) / FLIGHT
    src[land:] = np.minimum(DONOR_LAND + k[land:] - land, DONOR_END - 1)
    rots = np.empty((n, 23, 3, 3))
    for f in range(n):
        a = int(np.floor(src[f]))
        b, u = min(a + 1, len(vvalues) - 1), src[f] - a
        for c in range(23):
            rots[f, c] = _blend(drots[1][a, c], drots[1][b, c], u)
    # Rick's place: his hands at the catch where Marduk's are (on the victim, who starts where Marduk's does)
    place = mhands[0] - held[0]
    place[1] = 0.0
    hips = np.zeros((n, 3))
    for f in range(min(n, release + 1)):
        a = int(np.floor(src[f]))
        u = src[f] - a
        g = grip[a] + (grip[min(a + 1, len(grip) - 1)] - grip[a]) * u
        own = vpos[a, 0] + (vpos[min(a + 1, len(vpos) - 1), 0] - vpos[a, 0]) * u
        w = attacks.ease((src[f] - HELD_FROM[0]) / (HELD_FROM[1] - HELD_FROM[0]))
        hips[f] = own * (1 - w) + (held[min(f, len(held) - 1)] + place - rots[f, 2] @ rots[f, 3] @ g) * w
    # the flight: on from the release, TOSS forward, down onto the floor as Marduk's victim lies on it
    lying = vpos[DONOR_LAND, 0]
    p0 = hips[release]
    rick = tp[release][0] + feet[release] * rscale + place                 # his hips, as he lets go
    p1 = np.array([p0[0], lying[1], rick[2] + TOSS])
    dt = FLIGHT / 60.0
    vy = (p1[1] - p0[1] + 0.5 * GRAVITY * dt * dt) / dt
    for f in range(release, land + 1):
        s = (f - release) / 60.0
        hips[f] = [p0[0], p0[1] + vy * s - 0.5 * GRAVITY * s * s, p0[2] + (p1[2] - p0[2]) * s / dt]
    for f in range(land, n):                       # the landing slides on, and he lies as Marduk's victim does
        slide = SLIDE * attacks.ease((f - land) / SLIDE_FRAMES)
        d = vpos[int(src[f]), 0] - lying
        hips[f] = p1 + [d[0], d[1], d[2] + slide]
    print('grab: lift %d frames, release at %d (the opponent\'s hips %.0f mm up, %.0f behind Rick\'s), lands at %d '
          '%.0f mm in front of him; Rick\'s throw %d frames, the victim\'s %d' % (
              lift, release, p0[1], rick[2] - p0[2], land, p1[2] - rick[2], t['throw'], n))

    ground = feet + place / rscale
    print('grab: Rick starts %.0f mm behind the opponent\'s place (Marduk %.0f)' % (
        -ground[0][2] * rscale, -donor[0]['values'][0, 0, 2] * vscale))
    throw, hp, tp = retarget(THROW, ground=ground, **kw)
    pack, at = with_appended(pack, throw)
    if at != GRAB_ANIM + 1:
        raise ValueError('the grab\'s throw went to body animation %d, not %d' % (at, GRAB_ANIM + 1))

    # the victim's channels: Euler angles (raw), hips height in channel 1, the rest of his place in channel 0
    desc = retarget.stand['descriptors']
    values = np.tile(retarget.stand['values'][0], (n, 1, 1)).astype(np.float64)
    for f in range(n):
        for c, d in enumerate(animation.BODY_DESCRIPTORS):
            if animation.is_rotation(d):
                values[f, c] = bone.euler_xyz_from_matrix(rots[f, c])
            elif c == 6:
                values[f, c] = vvalues[int(src[f]), c]
        T = rots[f, 2]
        values[f, 1] = [0.0, hips[f][1] / vscale, 0.0]
        root = T @ (values[f, 1] * np.array([1, 1, -1])) * vscale
        values[f, 0] = (hips[f] - root) / vscale
        values[f, 0, 1] = 0.0
    victim = raw_animation(desc, values)
    pack, at = with_appended(pack, victim)
    if at != GRAB_ANIM + 2:
        raise ValueError('the grab\'s victim went to body animation %d, not %d' % (at, GRAB_ANIM + 2))
    print('grab: body animations %d (reach, %d frames), %d (throw, %d), %d (victim, %d)' % (
        GRAB_ANIM, REACH_FRAMES, GRAB_ANIM + 1, len(tp), GRAB_ANIM + 2, n))
    return pack

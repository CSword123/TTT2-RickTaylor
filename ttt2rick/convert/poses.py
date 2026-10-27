"""Rick's intros and match win pose: Splatterhouse's two idle alternates (playerbasicmovestates.smf: IdleAlt01,
IdleAlt02, which he plays when left standing), in place of Marduk's in his motion pack.

- Intros (Marduk's vt_srm / vt_slm, 360 frames, the team's first member, and vt_srs / vt_sls, 150 frames, its
  partner; his round-start list picks them): combatidle_atl1, Rick cracking his knuckles (hands together at the
  chest, Havok frames 12-40 and 56-84; it starts and ends in his combat stance). The first member's is held in the
  stance for INTRO_LEAD frames, then plays it all, then holds the stance to the end; the partner's plays the first
  crack and the way back to the stance (CRACK_SHORT), a little faster.
- Match win (vt_wnm_1, vt_1wm, 250 frames): idle_alt, Rick getting aggressive and flexing his arms, up to its last
  arms-raised moment (FLEX_END), then held. The pose's second parts (TTT2 plays a win in parts: the winner's, then
  one with the partner) that play Marduk's own animations hold that last frame as long as they lasted, as Petexy's
  port does with a donor's poses (pose_sequence); the shared pair poses (co_, mk_) stay.
The intros are turned so his shoulders lie as Marduk's do in his own intro (INTRO_SHOULDERS: square to the intro's
camera; his fight stance has them 45 degrees off it), facing the camera; the win is turned as his stance is
(ttt2rick.convert.idle STANCE_TURN, the stance's root turn). Each stays in place.
Marduk's intro and win moves also play a face animation (move property FACE_PROP: the motion pack's face bones), which
on Rick's body stretched his neck (the user saw it in the intro); ttt2rick.convert.attacks takes it off them (FACE_MOVES).
"""
import numpy as np

INTRO = 'combatidle_atl1.hkx'
WIN = 'idle_alt.hkx'
# Marduk's body animations (his motion pack's indices): intros of the first member and of the partner, the match win
INTROS_FULL, INTROS_SHORT = (0x292, 0x294), (0x293, 0x295)
WIN_ANIM = 0x296
# Marduk's own second parts of his match win (vt_wnm_*_2), held in the win pose: index -> frames
WIN_PARTS = {0x297: 258, 0x298: 342, 0x299: 366, 0x29A: 120, 0x29B: 120, 0x29C: 120, 0x29D: 120, 0x29E: 180}
INTRO_SHOULDERS = np.radians(-20.0)   # Marduk's shoulder line in his intro (left minus right shoulder, atan2(z, x))
FACE_PROP = 0x82F7               # a move's face animation (Marduk's vt_srm: 0x4003, the face pack's animation 3)
FACE_MOVES = 'vt_'               # the moves (by name prefix) of Marduk's intros, win and lose poses
CHIN_DOWN = np.radians(23.0)     # the intros' head tilt, chin down: the intro camera is low and looks up, and with his
                                 # head as in Splatterhouse it showed the front of his neck under the mask, long (the user
                                 # saw it); Splatterhouse's camera never looks at him from there
INTRO_LEAD = 45                  # frames (at 60) of the stance before the full intro's knuckle crack
CRACK_SHORT = [(0, 48), (92, 134)]   # Havok frame spans of the partner's intro: the first crack, back to the stance
FLEX_END = 97                    # Havok frame of the win's last arms-raised moment


def held(spans, frames, lead=0):
    """Havok frame numbers for `frames` output frames: `lead` frames of the first, then the spans played one after
    the other evenly over what is left, but no faster than twice Havok's 30 a second (then the last frame held)."""
    total = sum(b - a for a, b in spans)
    n = max(1, min(frames - lead, int(round(total * 2))))
    k = np.linspace(0, total, n)
    times, edges = [], np.cumsum([0] + [b - a for a, b in spans])
    for x in k:
        s = min(int(np.searchsorted(edges, x, side='right')) - 1, len(spans) - 1)
        times.append(spans[s][0] + x - edges[s])
    times = [spans[0][0]] * lead + times
    return np.array(times + [times[-1]] * (frames - len(times)), float)


def _rot(axis, a):
    x, y, z = axis / np.linalg.norm(axis)
    c, s, C = np.cos(a), np.sin(a), 1 - np.cos(a)
    return np.array([[c + x * x * C, x * y * C - z * s, x * z * C + y * s],
                     [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
                     [z * x * C - y * s, z * y * C + x * s, c + z * z * C]])


def chin_down(G, names):
    """The head (C_head_01, whose rotation the TTT2 head takes) turned CHIN_DOWN about his shoulder line."""
    G = G.copy()
    h, l, r = (names.index(n) for n in ('C_head_01_jnt', 'L_shoulder_jnt', 'R_shoulder_jnt'))
    for k in range(len(G)):
        axis = G[k, l, :3, 3] - G[k, r, :3, 3]
        axis[1] = 0.0
        G[k, h, :3, :3] = _rot(axis, CHIN_DOWN) @ G[k, h, :3, :3]
    return G


def with_poses(pack, retarget, stance):
    """The motion pack with the intros, the match win and its held parts replaced (stance: the stance's Havok
    animation, retargeted first: its root turn is theirs)."""
    from .idle import load_animation, with_animation
    yaw = retarget.yaws[stance]
    frames = load_animation(retarget.folder, INTRO, retarget.sk)['frames']
    full = held([(0, frames - 1)], 360, INTRO_LEAD)
    names = [n[4:] if n.startswith('cha:') else n for n in retarget.bon['names']]
    l, r = names.index('KATA_L_jnt'), names.index('KATA_R_jnt')

    def shoulders(y):
        tp = retarget(INTRO, times=full, yaw=y, adjust=chin_down)[2]
        d = np.mean([t[l] - t[r] for t in tp], 0)
        return np.arctan2(d[2], d[0])
    intro_yaw = yaw
    for _ in range(3):                  # the turn is about the vertical: the shoulder line turns with it, one for one
        a0, a1 = shoulders(intro_yaw), shoulders(intro_yaw + 0.1)
        step = (a1 - a0) / 0.1
        intro_yaw += (INTRO_SHOULDERS - a0) / step
    print('intros: shoulders at %.0f degrees (Marduk\'s %.0f), turned %.0f degrees from the stance' % (
        np.degrees(shoulders(intro_yaw)), np.degrees(INTRO_SHOULDERS), np.degrees(intro_yaw - yaw)))
    for index in INTROS_FULL:
        pack = with_animation(pack, index, retarget(INTRO, times=full, yaw=intro_yaw, adjust=chin_down)[0])
    short = held(CRACK_SHORT, 150)
    for index in INTROS_SHORT:
        pack = with_animation(pack, index, retarget(INTRO, times=short, yaw=intro_yaw, adjust=chin_down)[0])
    print('intros: %s, %d frames (body animations %s) and %d (%s)' % (
        INTRO, len(full), ', '.join('%#x' % i for i in INTROS_FULL), len(short),
        ', '.join('%#x' % i for i in INTROS_SHORT)))
    win = held([(0, FLEX_END)], 250)
    pack = with_animation(pack, WIN_ANIM, retarget(WIN, times=win, yaw=yaw)[0])
    for index, n in WIN_PARTS.items():
        pack = with_animation(pack, index, retarget(WIN, times=np.full(n, float(FLEX_END)), yaw=yaw)[0])
    print('match win: %s to its frame %d, held (body animation %#x; its second parts %s held)' % (
        WIN, FLEX_END, WIN_ANIM, ', '.join('%#x' % i for i in WIN_PARTS)))
    return pack

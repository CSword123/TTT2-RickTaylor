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
Splatterhouse pins his hips in place and steps his feet around them (its game slides him toward his target), so
each punch carries him (channel 0, the ground displacement) by its own footwork: every frame as far as the planted
foot moved back under him (footwork), so his feet stay put while he steps through. The runs (the ram, the lunge)
keep an eased charge of their own (`forward`), as footwork misses their airborne strides. Splatterhouse turns him toward his
target as he punches, and its right punch and spin are thrown off his facing (48 and 29 degrees): in TTT2, where
hitboxes are on the bones, they missed anything not pinned to a wall. So each attack is also turned (aim) until the
striking hand points straight ahead on its first active frame, the turn eased in over the windup and out again over
the recovery, so it still starts and ends in his stance.

The X button's chain in Splatterhouse (statemachines/player_initialrick/playercomboattackstates.smf) runs a haymaker,
a backhand with the same arm (AttackBackhandLeft/Right) and the 360 punch (360Punch, atk_punch_360, left arm). Its
right-hand chain is his 2, 2,2, 2,2,1 (the user's call, 2026-10-26: the right hand on 2):
- 2: Marduk's 2 (Va_rp00) playing the right haymaker (atk_punchr_high), at i12 (Marduk's: i10);
- 2,2: a move of his own (Va_rpbh_ric, a copy of Marduk's right follow-up Va_ttlprp) playing the right backhand
  (atk_backhand_r), from 2's frame FOLLOW_UP_FRAME, i17;
- 2,2,1: the spin (Va_ttlplp_ric), from 2,2's frame SPIN_FRAME, i20;
- 2,2,1,2: Splatterhouse's next X after the spin, the lariat (LariatPunch, atk_larriatpunch, right arm), a mid
  knockdown (Va_lariat_ric) lunging forward all the way (LUNGES), from the spin's frame LARIAT_FRAME, i22;
- 2,1: the left haymaker (atk_punchl_high) after the right one (Va_lhay_ric, a high), from FOLLOW_UP_FRAME, i17.
f+2 carries him a little further than its footwork (LUNGE_EXTRA, the user's call, 2026-10-27).
f+1+2 (in place of Marduk's Va_double) is Splatterhouse's barrage, its mashed X (BarragePunchA-H, atk_barrage01-04,
right fist first, at its own speed): a press throws two, held 1+2 up to eight (BARRAGE).
2 and 2,2 snap the head back standing (REACTIONS), so the next hit combos; the spin crumples, and the lariat (a mid)
still catches the crumpling opponent (2,1 and 2,2,1,2 are natural combos in game). b+1 and its strings are
Marduk's own again.

The 3+4 crouch is Splatterhouse's RT crouch (ttt2rick.convert.idle CROUCH), and its moves Splatterhouse's moves off it
(playersprintattackstates.smf): 1 is the running ram (RT+Y: RunRam_Begin -> RunRam_Loop -> runram_outro, the left
shoulder first), on a copy of Marduk's crouch tackle (Va_awtac, his f+1 from the crouch), a knockdown (sDw_KAO00_)
that runs on through the loop (TRAVEL_UNTIL) past the fallen opponent; 2 is the sweeping punch (RT+X:
Sprint_AtkPunch, runram_roundpunch, right fist), on a copy of his crouch f+2 (Va_sprp), a true low (HITLEVEL); 1+2 stays Marduk's
takedown (Va_spear, into his mount: Va_spear01, the opponent's Mt_ moves), its lunge playing Splatterhouse's (RT+B:
DashAttackGrab, tackle_miss), carried as far as Marduk's (1821 units at its contact frame 24), so the takedown,
which plays Marduk's own animations in step with the opponent's, starts where his would.

The spin gets Marduk's b+2's (Va_rp00B) two properties of its own (EXTRA): 0x81aa, which only that move has,
on 12 frames before its hit and off 2 after it (the faint white streak along the swing), and 0x80f8 = 2 from the
start (on 18 of his moves, mostly sidestep attacks and tag-in jumps: probably how it turns to the opponent).

The spin bounds in a juggle (BOUND): its hit conditions get TTT2's bound entry in front, [467 -> bound][466 -> air]
[...], the requirement and reaction Marduk's own bound moves use (dwup_hei_xe_ex), and with it TTT2's Tag Assault:
Petexy's tagsystem (third_party/petexy-ttt2: add_tag_assault, learnt from Marduk's 10 X -> XT -> XDA triples) gives
it the tag cancel during its startup into a twin that bounces for the partner and brings the partner in.

b+2 is Splatterhouse's Y (heavy) attack, which charges while Y is held (HeavyAttackIntro -> HeavyAttack (held)
-> HeavyRelease, an overhand arc punch; held on -> HeavyCharge -> HeavyPunch, a bigger overhead smash). Tapped, it
is Marduk's b+2 (Va_rp00B, i22) playing atk_arcpunch; with 2 still held at its frame HOLD_FRAME it cancels into a
move of his own (Va_rpst_ric, a copy of Marduk's Va_rpst00: a mid knockdown that slams an airborne opponent down,
30 damage, i24 from there: i36 from the press) playing atk_punchdown_r, which blends in from the arc punch's wound-up
pose. A held button in a cancel is its bit << 9 (2: 0x400), a released one its bit << 18 (2: 0x80000), as in
Jack-6's own charged b+2 (Jc_GUNrp00 -> Jc_GUN_4RPHLD on 0x400 at frame 15) and Lars's La_t_srpB02Hold.
"""
import os

import numpy as np

from ..splatterhouse import hkx

BLEND_IN = 6                     # frames at 60 fps from the stance's pose into an attack
# forward travel (ground displacement units, by the hit): Marduk's dash 1429; his 2 443, crouch f+1 784, crouch f+2
# 767, takedown lunge 1821 (at its contact frame 24)
# (the punches travel by their own footwork, FEET; the ram and the lunge are runs, whose airborne strides footwork
# undercounts: the ram reached 193 by its hit, so they keep a charge of their own)
RAM, LUNGE = 2600.0, 2020.0      # the lunge's ease is 90% there by its contact frame: 1821
FEET = None                      # travel: as far as the attack's own steps take him (footwork)
PLANT_MARGIN = 20.0              # mm the free foot must be under the planted one to take its place
# attacks that lunge forward all the way in Splatterhouse (the user's word, 2026-10-26: the lariat's spin pivots on a
# foot, which footwork read as 288 back by the hit): only their forward steps count
LUNGES = {'atk_larriatpunch.hkx'}
# travel added to an attack's footwork, eased in up to just after its hit (the user, 2026-10-26: the lariat should
# carry him forward a bit more; 2026-10-27: f+2, the right haymaker, a little more)
LUNGE_EXTRA = {'atk_larriatpunch.hkx': 600.0, 'atk_punchr_high.hkx': 300.0,
               # the barrage's punches keep up with the opponent each one pushes back (Splatterhouse slides him to
               # his target; in place, its second punch missed after a press and one held punch of eight)
               'atk_barrage01.hkx': 200.0, 'atk_barrage02.hkx': 200.0, 'atk_barrage03.hkx': 200.0,
               'atk_barrage04.hkx': 200.0}
FOLLOW_UP_FRAME = 25             # f+2's frame from which f+2,2 and f+2,1 come out (9 after its hit: they hit 26 after it,
                                 # inside its 30-frame reaction)
SPIN_FRAME = 28                  # 2,2's frame from which the spin comes out (11 after its hit)
LARIAT_FRAME = 27                # the spin's frame from which the lariat comes out (7 after its hit: at 11, with
                                 # i22, it sometimes came too late for the crumpling opponent)
BACKFIST_FRAME = 28              # f+2,1's frame from which the backfist comes out (11 after its hit)
STRAIGHT_FRAME = 34              # b+2's frame from which the straight comes out (12 after its hit: hits 30 after it,
                                 # inside its 40-frame reaction)
SMASH_FRAME = 29                 # the straight's frame from which the smash comes out (11 after its hit)
# 2 is i12; 2,2 i17 from the cancel, so it hits 29 frames after 2, inside 2's 40-frame standing reaction; the spin
# i20, 31 after 2,2 (its reaction 40 frames too). The ram's shoulder stays out from 16 to 26 (a charge: at 16-19
# alone it was still closing in, and whiffed in game)
STARTUP = {}
STARTUP_NEW = {'Va_rpbh_ric': (17, 19), 'Va_ttlplp_ric': (20, 22), 'Va_rpst_ric': (24, 25), 'Va_ram_ric': (16, 26),
               'Va_sweep_ric': (18, 19), 'Va_lhay_ric': (17, 19), 'Va_lariat_ric': (20, 22), 'Va_fhay_ric': (16, 17),
               'Va_lbh_ric': (17, 19), 'Va_strl_ric': (18, 20), 'Va_smash_ric': (22, 24)}
# damage of every hit-condition entry (Marduk's 2 10, Va_ttlprp 10, crouch f+1 16, f+2 22): the finishers do more
DAMAGE = {'Va_ttlplp_ric': 16, 'Va_rpst_ric': 30, 'Va_ram_ric': 18, 'Va_lariat_ric': 22, 'Va_lbh_ric': 14,
          'Va_strl_ric': 14, 'Va_smash_ric': 25}
# the frame a move ends (back to the stance), where its animation is longer than the copied move (Va_awtac ends at
# 40, Va_sprp at 50): the ram's outro and the sweep's follow-through play out
END = {'Va_ram_ric': 60, 'Va_sweep_ric': 58}
# automatic cancels left out of a copied move: Marduk's own variants of it, with his animation (Va_rpst00 goes to
# Va_rpst00_H on hit (requirement 46), an elbow, and to Va_rpst00Chg on a tag change; Va_awtac has a 2 follow-up)
DROP = {'Va_rpst_ric': ['Va_rpst00_H', 'Va_rpst00Chg'], 'Va_ram_ric': ['Va_awtacrp'],
        'Va_smash_ric': ['Va_rpst00_H', 'Va_rpst00Chg']}
# Marduk's body animation -> (Splatterhouse animation, its frame of full extension at 30 fps, Marduk's move that
# plays it, its first active frame at 60 fps, frames: Marduk's less the startup taken off; the striking hand, the
# forward travel)
ATTACKS = {
    # b+2: HeavyRelease, an overhead hammer: its fist is above his head until Havok frame 13 and comes down in front
    # of him by 14, so the hit is on the downswing (13.7), with a lunge like Marduk's own b+2's
    0x11E: ('atk_arcpunch.hkx', 13.7, 'Va_rp00B', 22, 80, 'R', FEET),
}
HOLD_FRAME = 12                  # b+2's frame at which 2 still held makes it the charged smash
# appended body animations, in order from SPIN_ANIM: (Splatterhouse animation, peak, frames, first active frame,
# the striking hand (None: not aimed), the forward travel, where its blend-in starts: None (the stance), 'crouch'
# (the 3+4 crouch) or (an ATTACKS index, its frame))
SPIN_ANIM = 685                  # after the guard (ttt2rick.convert.idle GUARD_ANIM 684)
RAM_FILES = 'runram_begin.hkx+runram_loop.hkx+runram_outro.hkx'   # 15 + 16 + 26 frames: the shoulder out by 18
NEW_ATTACKS = [('atk_punch_360.hkx', 14, 73, 20, 'L', FEET, None),                # 685 2,2,1: 360Punch (peak 14)
               ('atk_punchdown_r.hkx', 15, 79, 24, 'R', FEET, (0x11E, 12)),       # 686 b+2 held: HeavyPunch
               ('atk_punchr_high.hkx', 10, 48, 16, 'R', FEET, None),              # 687 f+2: AttackPunchRightHigh
               ('atk_backhand_r.hkx', 11, 66, 17, 'R', FEET, None),               # 688 2,2: AttackBackhandRight (whips through at 11)
               (RAM_FILES, 18, 64, 16, None, RAM, 'crouch'),                      # 689 3+4,1: RT+Y, the running ram
               ('runram_roundpunch.hkx', 15, 62, 18, 'R', FEET, 'crouch'),       # 690 3+4,2: RT+X, Sprint_AtkPunch
               ('tackle_miss.hkx', 12, 90, 24, None, LUNGE, 'crouch'),           # 691 3+4,1+2: RT+B, the lunge
               ('atk_punchl_high.hkx', 10, 50, 17, 'L', FEET, None),              # 692 f+2,1: AttackPunchLeftHigh
               ('atk_larriatpunch.hkx', 16, 73, 20, 'R', FEET, None),             # 693 f+2,2,1,2: LariatPunch (right arm out at 16)
               ('atk_backhand_l.hkx', 11, 66, 17, 'L', FEET, None),               # 694 f+2,1,1: AttackBackhandLeft (whips through at 11)
               ('atk_punchstraight_l.hkx', 15, 60, 18, 'L', FEET, (0x11E, STRAIGHT_FRAME)),   # 695 b+2,1: StraightPunchLeft
               ('atk_2handgroundpound.hkx', 17, 80, 22, 'R', FEET, None),         # 696 b+2,1,1+2: Smash (fists down past the chest at 17)
               # f+1+2: the barrage (BarragePunchA-H), at Splatterhouse's speed (rate 2: a Havok frame a frame)
               ('atk_barrage01.hkx', 10, 31, 10, 'R', FEET, None),               # 697 BarragePunchA, E: right
               ('atk_barrage02.hkx', 12, 36, 12, 'L', FEET, None),               # 698 BarragePunchB, F: left
               ('atk_barrage03.hkx', 9, 31, 9, 'R', FEET, None),                 # 699 BarragePunchC, G: right
               ('atk_barrage04.hkx', 9, 36, 9, 'L', FEET, None)]                 # 700 BarragePunchD, H: left
# Marduk's moves given an appended animation (by its index in NEW_ATTACKS)
ANIMS = {'Va_spear': SPIN_ANIM + 6}
# Rick's own moves: (name, the move copied, its body animation, hitbox from, after moves, button, the cancel's frame:
# None: where the copied move's own cancel from `after` is; 'like': as the first `after` row of LIKE's)
LEFT_ARM = 'Va_lp00B'            # hitbox 0d0c: left hand and forearm (right: 0908, Va_rp00's 09)
CROUCH_MOVES = ['Va_awKAM_st', 'Va_awKAM_', 'Va_awKAM_g', 'Va_awKAM_L', 'Va_awKAM_R']   # the crouch's own lists
LIKE = 'Va_spear'                # the crouch's moves come out when its 1+2 does (frame 10 in, 28 in a sidestep)
NEW_MOVES = [('Va_fhay_ric', 'Va_rp00', SPIN_ANIM + 2, 'Va_rp00', [], 0x40000002, ('take', 'Va_Binta00', 0x40)),
             ('Va_rpbh_ric', 'Va_ttlprp', SPIN_ANIM + 3, 'Va_rp00', ['Va_fhay_ric'], 0x40000002, FOLLOW_UP_FRAME),
             ('Va_ttlplp_ric', 'Va_ttlprp', SPIN_ANIM, LEFT_ARM, ['Va_rpbh_ric'], 0x40000001, SPIN_FRAME),
             ('Va_rpst_ric', 'Va_rpst00', SPIN_ANIM + 1, 'Va_rp00B', ['Va_rp00B'], 0x2 << 9, HOLD_FRAME),
             ('Va_ram_ric', 'Va_awtac', SPIN_ANIM + 4, 'Va_awtac', CROUCH_MOVES, 0x40000001, 'like'),
             ('Va_sweep_ric', 'Va_sprp', SPIN_ANIM + 5, 'Va_rp00', CROUCH_MOVES, 0x40000002, 'like'),
             ('Va_lhay_ric', 'Va_ttlprp', SPIN_ANIM + 7, LEFT_ARM, ['Va_fhay_ric'], 0x40000001, FOLLOW_UP_FRAME),
             ('Va_lariat_ric', 'Va_ttlprp', SPIN_ANIM + 8, 'Va_rp00', ['Va_ttlplp_ric'], 0x40000002, LARIAT_FRAME),
             ('Va_lbh_ric', 'Va_ttlprp', SPIN_ANIM + 9, LEFT_ARM, ['Va_lhay_ric'], 0x40000001, BACKFIST_FRAME),
             ('Va_strl_ric', 'Va_ttlprp', SPIN_ANIM + 10, LEFT_ARM, ['Va_rp00B'], 0x40000001, STRAIGHT_FRAME),
             ('Va_smash_ric', 'Va_rpst00', SPIN_ANIM + 11, 'Va_rp00', ['Va_strl_ric'], 0x40000003, SMASH_FRAME)]
# f+1+2, the barrage: Splatterhouse's BarragePunchA-H (mashed X), right and left in turn. A takes Marduk's f+1+2
# (Va_double) and ends in B (CHAIN), so a press throws two; each next one comes out while 1+2 is held (0x3 << 9) at
# Splatterhouse's frame of that transition (BarragePunchB -> C at 15, C -> D 12, D -> E 14, E -> F 11, F -> G 15,
# G -> H 12; A -> B 11), up to H, eight in all
BARRAGE = [('Va_brgA_ric', 0, 'Va_rp00', None, None), ('Va_brgB_ric', 1, LEFT_ARM, 'Va_brgA_ric', None),
           ('Va_brgC_ric', 2, 'Va_rp00', 'Va_brgB_ric', 15), ('Va_brgD_ric', 3, LEFT_ARM, 'Va_brgC_ric', 12),
           ('Va_brgE_ric', 0, 'Va_rp00', 'Va_brgD_ric', 14), ('Va_brgF_ric', 1, LEFT_ARM, 'Va_brgE_ric', 11),
           ('Va_brgG_ric', 2, 'Va_rp00', 'Va_brgF_ric', 15), ('Va_brgH_ric', 3, LEFT_ARM, 'Va_brgG_ric', 12)]
BARRAGE_ANIM = SPIN_ANIM + 12                   # its four animations (NEW_ATTACKS 697-700)
BARRAGE_LENGTH = [31, 36, 31, 36]               # their frames, where each hit ends unless the next comes
NEW_MOVES += [(name, 'Va_rp00', BARRAGE_ANIM + k, hitbox, [after] if frame else [], 0x3 << 9, frame)
              if after else (name, 'Va_rp00', BARRAGE_ANIM + k, hitbox, [], 0x40000003, ('take', 'Va_double', 0x40))
              for name, k, hitbox, after, frame in BARRAGE]
CHAIN = {'Va_brgA_ric': ('Va_brgB_ric', 11)}    # move -> (the move it goes on to by itself, at that frame)
ONLY = [b[0] for b in BARRAGE]                  # moves whose cancel list (Marduk's 2's) keeps only the moves of Rick's
                                                # own in it and its end
# move -> extra properties added, (frame, id, value); frame 0x8001: from the move's start (as Marduk's b+2 has them)
EXTRA = {'Va_ttlplp_ric': [(0x8001, 0x80f8, 2), (8, 0x81aa, 1), (24, 0x81aa, 0)]}
BOUND = ['Va_ttlplp_ric']
# move -> (its reaction to replace, the new one), by the reactions' normal-hit (default) moves: 2, 2,2 and 2,1 leave
# the opponent standing (face hits: 30 frames after 2, 40 after 2,2 and 2,1), the spin crumples; f+2,1,1 (the left
# backhand) snaps the head back as f+2,2 (the right one) does (the user's call, 2026-10-27). A reaction move
# without the bit 0x8 in its bitfield (Marduk's 2's sDm_KAOR27G_Va, and sDm_Rhd40GY, sDm_Lhd00(G) this file used)
# shakes the screen as the opponent takes the hit; these have it, as the jab's and 1,2's (measured in game,
# 2026-10-26: the user found 2,2 and 2,1 still shook)
REACTIONS = {'Va_fhay_ric': ('sDm_KAOR27G_Va', 'sDm_IKAO00R'), 'Va_rpbh_ric': ('sDm_KAKLcrG', 'sDm_IKAO_pl'),
             'Va_ram_ric': ('sDm_Sty00_', 'sDw_KAO00_'),   # the ram knocks down (Va_awtac's only staggered)
             'Va_lhay_ric': ('sDm_KAKLcrG', 'sDm_IKAO_pl'), 'Va_ttlplp_ric': ('sDm_KAKLcrG', 'sDm_KAKLcr'),
             'Va_lariat_ric': ('sDm_KAKLcrG', 'sDw_KAO00_'), 'Va_lbh_ric': ('sDm_KAKLcrG', 'sDm_IKAO_pl'),
             'Va_strl_ric': ('sDm_KAKLcrG', 'sDm_IKAO_pl')}
# hit levels (low byte: 0x10f low, 0x217 mid, 0x512 high; 0x200000 marks a heavy hit, which shakes the screen: Marduk's
# haymakers and power moves have it, and Va_ttlprp's copies with it): none of the 2,2,1,2 string has it (the user
# found its shakes excessive, 2026-10-26), the sweep a true low, the left haymaker a high like 2
# moves without the extra property 0x8001, which Marduk's 2 and his Va_ttlprp (so its copies) have, as his power
# moves (b+1, the headbutts, the stomp): it shakes the screen on a hit (measured in game, 2026-10-26, the
# background's shift frame to frame over a burst of frames: 2 shook for 12 frames on a hit, the jab and 1,2 not)
NO_SHAKE = ['Va_fhay_ric', 'Va_rpbh_ric', 'Va_lhay_ric', 'Va_ttlplp_ric', 'Va_lariat_ric', 'Va_lbh_ric', 'Va_strl_ric']
HITLEVEL = {'Va_rpbh_ric': 0x217, 'Va_ttlplp_ric': 0x217, 'Va_sweep_ric': 0x10f, 'Va_lhay_ric': 0x512,
            'Va_lariat_ric': 0x217, 'Va_lbh_ric': 0x217, 'Va_strl_ric': 0x217}
# the barrage's hits: active from the fist's full extension for 3 frames, ending with their animations, light
# (a press's two 5 each, the held ones 4: 34 for all eight), each a head snap that holds the opponent for the next
# one (as 2's), and no screen shake
for _name, _k, _, _, _ in BARRAGE:
    _peak = [10, 12, 9, 9][_k]
    STARTUP_NEW[_name] = (_peak, _peak + 2)
    END[_name] = BARRAGE_LENGTH[_k]
    DAMAGE[_name] = 5 if _name in ('Va_brgA_ric', 'Va_brgB_ric') else 4
    REACTIONS[_name] = ('sDm_KAOR27G_Va', 'sDm_IKAO00R')
    NO_SHAKE.append(_name)
# the frame by which an attack's travel is all done (default: a few frames after its hit): the ram runs on through
# its loop (to frame 34, where runram_outro starts) instead of charging in place once it hit
TRAVEL_UNTIL = {RAM_FILES: 34}


def retime(frames_src, peak, frames_dst, impact):
    """Havok frame numbers for each of frames_dst output frames: 0..peak over 0..impact, peak..end over the rest."""
    k = np.arange(frames_dst, dtype=float)
    before = k * peak / impact
    after = peak + (k - impact) * (frames_src - 1 - peak) / max(1, frames_dst - 1 - impact)
    return np.where(k <= impact, before, after)


def ease(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def travel(frames, impact, forward, until=None):
    """(frames, 3) ground displacement: `forward` along z, eased from BLEND_IN to a few frames after the hit (or to
    frame `until`)."""
    k = np.arange(frames, dtype=float)
    out = np.zeros((frames, 3))
    end = until if until is not None else impact + 4
    out[:, 2] = forward * ease((k - BLEND_IN) / max(1, end - BLEND_IN))
    return out


def footwork(tposes, bon, forward_only=False):
    """(frames, 3) ground displacement that keeps the planted foot where it is: Splatterhouse pins his hips and
    steps his feet around them (its game slides him toward the target), so each frame he travels (along z) as far
    as the planted ankle moved back under him. The planted foot is the lower ankle; the other one takes over only
    once it is PLANT_MARGIN lower, so a foot rolling onto its toes is not mistaken for a step. The game multiplies
    channel 0 by the skeleton's scale, as it does the root (fitted on Marduk's own walks). forward_only: the steps
    that would take him back (a foot pivoting in a spin) are left out, so he only ever goes forward."""
    names = [n[4:] if n.startswith('cha:') else n for n in bon['names']]
    ankles = np.array([[t[names.index('ASHI_%s_jnt' % s)] for s in 'LR'] for t in tposes])   # (frames, 2, 3)
    out = np.zeros((len(tposes), 3))
    planted = int(np.argmin(ankles[0, :, 1]))
    for f in range(1, len(tposes)):
        other = 1 - planted
        if ankles[f, other, 1] < ankles[f, planted, 1] - PLANT_MARGIN:
            planted = other
        step = -(ankles[f, planted, 2] - ankles[f - 1, planted, 2]) / float(bon['scale'])
        out[f, 2] = out[f - 1, 2] + (max(step, 0.0) if forward_only else step)
    return out


def aim(frames, impact):
    """0..1 per frame: how much of the aiming turn is on (in over the windup, held a few frames, out by the end)."""
    k = np.arange(frames, dtype=float)
    return np.where(k <= impact + 4, ease(k / (impact + 4)),
                    1 - ease((k - impact - 4) / max(1, frames - 1 - impact - 4)))


def _attack(retarget, start, name, peak, frames, impact, hand, forward, stance):
    """(raw animation, Havok joints, TTT2 joints) of an attack: retimed, turned to aim (unless hand is None: a ram, a
    lunge, led by the body), carried forward (forward None: by its own footwork)."""
    from .idle import load_animation
    an = load_animation(retarget.folder, name, retarget.sk)
    times = retime(an['frames'], peak, frames, impact)
    base = retarget.yaws[stance]
    kw = dict(times=times, blend_from=(start, BLEND_IN))
    if forward is not None:
        kw['ground'] = travel(frames, impact, forward, TRAVEL_UNTIL.get(name))
    yaw = base
    if hand is not None:
        names = [n[4:] if n.startswith('cha:') else n for n in retarget.bon['names']]
        h = names.index('TE_%s_jnt' % hand)
        _, _, tp = retarget(name, yaw=base, **kw)
        x, _, z = tp[impact][h]
        off = np.arctan2(x, z)                      # the hand's direction from straight ahead (+z)
        yaw = base + off * aim(frames, impact)
    out = retarget(name, yaw=yaw, **kw)
    if forward is None:
        kw['ground'] = footwork(out[2], retarget.bon, name in LUNGES) + travel(frames, impact,
                                                                                LUNGE_EXTRA.get(name, 0.0))
        out = retarget(name, yaw=yaw, **kw)
        g = kw['ground'][:, 2]
        print('%s: its footwork carries it %.0f by the hit, %.0f in all' % (name, g[impact], g[-1]))
    if hand is not None:
        x, _, z = out[2][impact][h]
        print('%s: aimed %.0f degrees (the %s hand now %.0f off)' % (name, np.degrees(off), hand,
                                                                     np.degrees(np.arctan2(x, z))))
    return out


def _stance_pose(retarget, stance):
    from .idle import FPS, load_animation, sample
    return sample(load_animation(retarget.folder, stance, retarget.sk), retarget.sk, FPS)[0]


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
    for k, (name, peak, frames, impact, hand, forward, origin) in enumerate(NEW_ATTACKS):
        pose = start
        if origin == 'crouch':                          # out of the 3+4 crouch
            from .idle import CROUCH
            pose = _stance_pose(retarget, CROUCH)
        elif origin is not None:                        # the pose of an ATTACKS animation at one of its frames
            from .idle import sample
            src, src_peak, _, src_impact, src_frames = ATTACKS[origin[0]][:5]
            an = hkx.animation(hkx.Packfile(open(os.path.join(retarget.folder, src), 'rb').read()))
            t = retime(an['frames'], src_peak, src_frames, src_impact)[origin[1]]
            pose = sample(an, retarget.sk, 60.0, [t])[0]
        anim, hp, tp = _attack(retarget, pose, name, peak, frames, impact, hand, forward, stance)
        pack, index = with_appended(pack, anim)
        if index != SPIN_ANIM + k:
            raise ValueError('%s went to body animation %d, not %d' % (name, index, SPIN_ANIM + k))
        shown[index] = (hp, tp)
        print('%s -> new body animation %d (%#x): %d frames, its frame %d at frame %d' % (
            name, index, 0x4000 + index, frames, peak, impact))
    return pack, shown


def edit_moveset(m):
    """Rick's moveset (a motbin.read of RIC1, its other changes made) rebuilt with ANIMS and NEW_MOVES: each new move
    appended (a copy, its own name, body animation and hitbox), and each move that gets a new follow-up given a copy
    of its cancel list at the end of the table with the follow-up in it, so no index moves."""
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
    def startup(i, name, first, last):
        d = moves[i]['first_active'] - first
        moves[i]['first_active'], moves[i]['last_active'] = first, last
        for r in own(i, 'cancel', 'cancels', lambda r: r['direction'] == 0x8000):
            if r['direction'] == 0x8000:                      # the move's end
                r['win_start'] -= d
                r['start_frame'] -= d
        for r in own(i, 'extraprops', 'extra_move_properties', lambda r: r['frame'] == 0 and r['id'] == 0):
            if 0 < r['frame'] < 0x4000:              # from 0x4000 on not a frame (0x8001: from the start)
                r['frame'] = max(1, r['frame'] - d)
        print('%s: i%d (%d frames earlier, its end too)' % (name, first, d))
    for name, (first, last) in STARTUP.items():
        startup(names.index(name), name, first, last)
    for name, anim in ANIMS.items():
        moves[names.index(name)]['anim'] = 0x4000 + anim
        print('%s: body animation %d' % (name, anim))
    made = {}                                       # new move name -> its index
    template = None                                 # the last button cancel row seen
    index = lambda n: made[n] if n in made else names.index(n)
    for name, copy, anim, hitbox_from, afters, button, frame in NEW_MOVES:
        move = dict(moves[names.index(copy)])
        move['name'] = len(strings)
        strings += name.encode('latin1') + b'\0'
        move['anim'] = 0x4000 + anim
        move['hitbox'] = moves[names.index(hitbox_from)]['hitbox']
        moves.append(move)
        made[name] = len(moves) - 1
        if isinstance(frame, tuple) and frame[0] == 'take':     # its input: every row that went to `frame[1]` on
            _, old, direction = frame                          # this button and direction now goes to it
            taken = 0
            for table in ('cancels', 'group_cancels'):
                for r in m.tables[table]:
                    if r['move_id'] == names.index(old) and r['button'] == button and r['direction'] == direction:
                        r['move_id'] = len(moves) - 1
                        taken += 1
            print('%s (move %d, body animation %d) takes %d input rows of %s' % (name, len(moves) - 1, anim, taken, old))
        for after in afters:
            i = index(after)
            rows = [dict(r) for r in cancel_list(i)]
            if frame is None:
                like = next(r for r in rows if r['move_id'] == names.index(copy))
                rows.insert(rows.index(like), dict(like, button=button, move_id=len(moves) - 1))
            elif frame == 'like':                   # as the list's row for LIKE (its window, its requirement), after
                like = next(r for r in rows if r['move_id'] < 0x8000 and r['move_id'] == names.index(LIKE))
                # it and the directional presses after it (dir 0, any direction, is matched in order: Marduk lists
                # 1+2 before 1, f+1 before 1), before any other neutral press and the sidestep and end rows
                at = rows.index(like) + 1
                while at < len(rows) and rows[at]['direction'] < 0x8000 and not (
                        rows[at]['direction'] == 0 and rows[at]['button'] & 3):
                    at += 1
                rows.insert(at, dict(like, button=button, move_id=len(moves) - 1))
            else:                                   # like the list's button rows (always, extradata 386), at frame;
                first = next((r for r in rows if r['button'] & 0x40000000), None)   # a list with none (2,2's: the
                if first is not None:                                               # move's end only) as the last
                    template = first
                # a press is taken from the move's start and comes out at `frame` (Marduk's strings: win 1-28, start
                # 28); a held button (no 0x40000000) is checked at that frame only
                like = dict(template, win_start=1 if button & 0x40000000 else frame, win_end=frame, start_frame=frame)
                rows.insert(rows.index(first) if first is not None else len(rows) - 1,
                            dict(like, direction=0, button=button, move_id=len(moves) - 1))
            moves[i]['cancel'] = len(cancels)
            cancels.extend(rows)
            print('%s (move %d, body animation %d) after %s on button %#x, from frame %d' % (
                name, len(moves) - 1, anim, after, button, like['start_frame']))
    for name, (first, last) in STARTUP_NEW.items():
        startup(made[name], name, first, last)
    for name, end in END.items():
        for r in own(index(name), 'cancel', 'cancels', lambda r: r['direction'] == 0x8000):
            if r['direction'] == 0x8000:
                r['win_start'] = r['start_frame'] = end
        print('%s: ends at frame %d' % (name, end))
    for name, drop in DROP.items():
        i = made[name] if name in made else names.index(name)
        rows = [dict(r) for r in cancel_list(i) if not (r['move_id'] < len(names) and names[r['move_id']] in drop)]
        moves[i]['cancel'] = len(cancels)
        cancels.extend(rows)
        print('%s: no cancels into %s' % (name, ', '.join(drop)))
    for name in ONLY:
        i = index(name)
        rows = [dict(r) for r in cancel_list(i) if r['direction'] == 0x8000 or r['move_id'] in made.values()]
        moves[i]['cancel'] = len(cancels)
        cancels.extend(rows)
        mine = {v: k for k, v in made.items()}
        print('%s: cancels only into %s' % (name, ', '.join(mine.get(r['move_id'], '%#x' % r['move_id'])
                                                            for r in rows)))
    for name, (to, frame) in CHAIN.items():         # an automatic cancel (no button, no requirement: req 0, as the
        i = index(name)                             # button rows'), before the move's end row; an end row that goes
        rows = [dict(r) for r in cancel_list(i)]    # to a move only does so at the move's end
        end = next(k for k, r in enumerate(rows) if r['direction'] == 0x8000)
        rows.insert(end, dict(rows[end], direction=0, button=0, req=0, extradata=0xe, win_start=1, win_end=frame,
                              start_frame=frame, move_id=index(to)))
        moves[i]['cancel'] = len(cancels)
        cancels.extend(rows)
        print('%s: goes on to %s at frame %d' % (name, to, frame))
    # after NEW_MOVES: their copies keep the moves' old reactions
    reactions = m.tables['reactions']
    hit_end = lambda h: h['req'] is None or m.tables['requirements'][h['req']]['condition'] == 690   # no condition
    for name, (old, new) in REACTIONS.items():
        i = index(name)
        to = next(k for k, r in enumerate(reactions) if r['default'] is not None and r['default'] < len(names)
                  and names[r['default']] == new)
        for h in own(i, 'hit_condition', 'hit_conditions', hit_end):
            r = reactions[h['reactions']] if h['reactions'] is not None else None
            if r is not None and r['default'] is not None and r['default'] < len(names) and names[r['default']] == old:
                h['reactions'] = to
        print('%s: hit reaction %s -> %s (reactions %d)' % (name, old, new, to))
    props = m.tables['extra_move_properties']
    for name, added in EXTRA.items():
        i = made[name] if name in made else names.index(name)
        old = [] if moves[i]['extraprops'] is None else [
            dict(e) for _, e in m.iter_list('extra_move_properties', moves[i]['extraprops'],
                                            lambda e: e['frame'] == 0 and e['id'] == 0)]
        end = old.pop() if old and old[-1]['frame'] == 0 and old[-1]['id'] == 0 else dict(frame=0, id=0, value=0)
        moves[i]['extraprops'] = len(props)
        props.extend([dict(frame=f, id=k, value=v) for f, k, v in added] + old + [end])
        print('%s: extra properties %s' % (name, ', '.join('%#x=%d at %s' % (k, v, 'start' if f == 0x8001 else f)
                                                           for f, k, v in added)))
    for name, level in HITLEVEL.items():
        moves[index(name)]['hitlevel'] = level
        print('%s: hit level %#x' % (name, level))
    from .poses import FACE_MOVES, FACE_PROP
    faced = 0
    for i, mv in enumerate(moves[:len(names)]):           # Marduk's own (the appended ones have none)
        if not names[i].startswith(FACE_MOVES) or mv['extraprops'] is None:
            continue
        rows = [dict(e) for _, e in m.iter_list('extra_move_properties', mv['extraprops'],
                                                 lambda e: e['frame'] == 0 and e['id'] == 0)]
        if any(e['id'] in (FACE_PROP, 0x8300, 0x82DB, 0x82DC) for e in rows):
            mv['extraprops'] = len(props)
            props.extend(e for e in rows if e['id'] not in (FACE_PROP, 0x8300, 0x82DB, 0x82DC))
            faced += 1
    print('face animation (%#x) taken off %d of Marduk\'s pose moves' % (FACE_PROP, faced))
    for name in NO_SHAKE:
        i = index(name)
        if moves[i]['extraprops'] is None:
            continue
        rows = [dict(e) for _, e in m.iter_list('extra_move_properties', moves[i]['extraprops'],
                                                 lambda e: e['frame'] == 0 and e['id'] == 0)]
        moves[i]['extraprops'] = len(props)
        props.extend(e for e in rows if e['id'] != 0x8001)
        print('%s: no extra property 0x8001 (%d left)' % (name, len(rows) - 1 - sum(e['id'] == 0x8001 for e in rows)))
    hit_list_end = lambda h: h['req'] is None or m.tables['requirements'][h['req']]['condition'] == 690
    for name, damage in DAMAGE.items():
        i = made[name] if name in made else names.index(name)
        for h in own(i, 'hit_condition', 'hit_conditions', hit_list_end):
            if h['damage']:
                h['damage'] = damage
        print('%s: damage %d' % (name, damage))
    if BOUND:
        import collections
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'third_party', 'petexy-ttt2', 'tools',
                                        'characters'))
        from ttt2char.convert import tagsystem as TS
        t = m.tables
        req, after = TS.bound_shape(t)
        bound = collections.Counter(h['reactions'] for h in t['hit_conditions']
                                    if h['reactions'] is not None and TS.has(t, h['req'], TS.BOUND)).most_common(1)[0][0]
        tpl = TS.assault_template(t, m.aliases)
        for name in BOUND:
            i = made[name] if name in made else names.index(name)
            hs = [dict(h) for h in TS.hits(t, moves[i]['hit_condition'])]
            moves[i]['hit_condition'] = TS.write(t, 'hit_conditions', [dict(req=req, damage=hs[0]['damage'],
                                                                            reactions=bound)] + hs)

        def name_of(i):                             # names of the moves made here are in the new string block
            off = moves[i]['name']
            return bytes(strings[off:strings.index(0, off)]).decode('latin1')

        def string(n):
            off = len(strings)
            strings.extend(n.encode('latin1') + b'\0')
            return off
        first = min(made[n] if n in made else names.index(n) for n in BOUND)
        for x, xt, xda in TS.add_tag_assault(t, tpl, first, name_of, string):
            print('%s: bounds (%s), Tag Assault through %s / %s (learnt from %d of Marduk\'s)' % (
                name_of(x), names[t['reactions'][bound]['default']], name_of(xt), name_of(xda), tpl['triples']))
    return motbin.build(header, bytes(strings), m.tables, mota_blob, mota_slots)

"""Jennifer's motion pack: Rick's (ttt2rick.convert.idle's, Marduk's with Rick's stance, guard and attacks), its
feet planted for her legs.

python -m ttt2jen.motions <Rick's motion pack (key_52494332.bin)> <ric.bon> <jen.bon> <out dir>
Writes <out dir>/key_4a454e32.bin ("JEN2", JEN_MOTIONS): recomp/runtime/rick_slot.cpp gives it to Rick's motion row
under TTT2_JEN=1.

The game multiplies an animation's root position (channel 1) by the skeleton's scale, so Rick's moves on her already
come out her size; but her legs are not his legs scaled (her thighs and shins are longer for her hips), and his stance
bends his knees: with his root height her soles went into the floor. In every Euler (0xC8) body animation, each
frame's root height is moved so that her lower ankle is as far over its planted height as Rick's is over his (scaled
by the skeletons' scales): planted where his is planted. The compressed (0x64) animations, Marduk's own, are kept.

Arms: Rick's stance and guard hold his upper arms about 25 degrees behind his chest (around his broad back); on her
narrow frame the far arm came out behind her back. In those two (ARM_POSES) each upper arm is swung forward, about
the chest's side axis, to at most ARM_BACK degrees behind the chest; the forearm and hand follow it. His attacks keep
their arms, so they still reach where his do (the game blends from the stance into them).
"""
import os
import sys

import numpy as np

from ttt2rick.convert import idle
from ttt2rick.convert.rick import _rotation
from ttt2rick.ttt2 import fk, xbox
from ttt2rick.ttt2.petexy import animation, bone

ANKLES = ('ASHI_L_jnt', 'ASHI_R_jnt')
JEN_MOTIONS = 0x4A454E32        # "JEN2": rick_slot.cpp kJenMotions
ARM_POSES = (idle.STAND_ANIM, idle.GUARD_ANIM)
ARM_BACK = np.radians(5.0)


def ankles(bon, values):
    """(frames, 2) world heights of the ankles under an Euler animation's channels (FK of the channel bones)."""
    bi = fk.bone_index(bon)
    out = np.zeros((len(values), 2))
    for f, vals in enumerate(values):
        rots = {bi[b]: bone.matrix_from_euler_xyz(vals[c]) for c, b in fk.CHANNEL_BONES.items()}
        W = fk.world(bon, rots, vals[1] * np.array([1, 1, -1]) * float(bon['scale']))
        out[f] = [W[bi[a]][1, 3] for a in ANKLES]
    return out


def arms_forward(bon, values):
    """values with each upper arm (KATA channel) swung forward to at most ARM_BACK behind the chest."""
    bi = fk.bone_index(bon)
    rest = bone.world_matrices(bon)
    chan = {b: c for c, b in fk.CHANNEL_BONES.items()}
    out = values.copy()
    for f, vals in enumerate(values):
        rots = {bi[b]: bone.matrix_from_euler_xyz(vals[c]) for c, b in fk.CHANNEL_BONES.items()}
        W = fk.world(bon, rots, vals[1] * np.array([1, 1, -1]) * float(bon['scale']))
        C = W[bi['MUNE2_jnt']][:3, :3] @ rest[bi['MUNE2_jnt']][:3, :3].T      # the chest's turn from rest
        fwd, side = C @ [0.0, 0, 1], C @ [1.0, 0, 0]
        for S in 'LR':
            kata = bi['KATA_%s_jnt' % S]
            d = W[bi['UDE_%s_jnt' % S]][:3, 3] - W[kata][:3, 3]
            d /= np.linalg.norm(d)
            back = np.arcsin(np.clip(-d @ fwd, -1, 1))
            if back <= ARM_BACK:
                continue
            # the turn about the side axis that brings it to ARM_BACK: in the plane across the side axis
            flat = d - side * (d @ side)
            want = flat * np.cos(back - ARM_BACK) + np.cross(side, flat) * np.sin(back - ARM_BACK) * np.sign(
                np.cross(side, flat) @ fwd)
            want = want + side * (d @ side)
            R = _rotation(d, want)
            parent = W[bon['parent'][kata]][:3, :3]
            out[f, chan['KATA_%s_jnt' % S]] = bone.euler_xyz_from_matrix(parent.T @ R @ W[kata][:3, :3])
    return out


def planted(bon):
    """The ankles' heights with the foot flat on the floor (the skeleton's parameters 1, 2 times its scale)."""
    return np.array(bon['params'][1:3]) * float(bon['scale'])


def refit(pack, rick, jen):
    o0, offs = idle.mota(pack)
    ratio = float(jen['scale'] / rick['scale'])
    done = 0
    for index, off in enumerate(offs):
        if not off:
            continue
        an = animation.decode(pack, '>', o0 + off)
        if an['type'] != 200:
            continue
        values = an['values'].copy()
        if index in ARM_POSES:
            values = arms_forward(jen, values)
        over = (ankles(rick, values) - planted(rick)).min(1) * ratio      # Rick's lower foot over the floor, scaled
        mine = (ankles(jen, values) - planted(jen)).min(1)
        values[:, 1, 1] += (over - mine) / float(jen['scale'])
        pack = idle.with_animation(pack, index, idle.raw_animation(an['descriptors'], values))
        o0, offs = idle.mota(pack)
        done += 1
    return pack, done


def main(rick_pack, rick_bon, jen_bon, out):
    rick = xbox.read_bone(open(rick_bon, 'rb').read())
    jen = xbox.read_bone(open(jen_bon, 'rb').read())
    pack, done = refit(open(rick_pack, 'rb').read(), rick, jen)
    out = os.path.join(out, 'key_%08x.bin' % JEN_MOTIONS)
    open(out, 'wb').write(pack)
    print('%s: %d animations refitted, %d bytes' % (out, done, len(pack)))


if __name__ == '__main__':
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    main(*sys.argv[1:])

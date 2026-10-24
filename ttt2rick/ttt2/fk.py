"""Forward kinematics of a TTT2 fighter's body animation: the 23 body channels on the .bon skeleton.

Channel -> bone (the game's table; Petexy's ttt2/animation.py): 3 HARA_ROT1, 4 MUNE1, 5 KOSHI, 7 KUBI, 8 ATAMA, 9-12
SAKOTSU_R KATA_R UDE_R TE_R, 13-16 the same on the left, 17-19 MOMO_R HIZA_R ASHI_R, 20-22 MOMO_L HIZA_L ASHI_L.
Channel 1 is the model root's (HARA_ROT1's) position, its z negated by the game's sampler. A bone's local
translation is the skeleton's, its local rotation the channel's (replacing the skeleton's); other bones keep their
skeleton rotation. (MUNE1's rotation is spread over MUNE1 and MUNE2 by the game; here MUNE1 takes it all.)
"""
import numpy as np

from .petexy import bone

CHANNEL_BONES = {3: 'HARA_ROT1', 4: 'MUNE1_jnt', 5: 'KOSHI_jnt', 7: 'KUBI_jnt', 8: 'ATAMA_jnt',
                 9: 'SAKOTSU_R_jnt', 10: 'KATA_R_jnt', 11: 'UDE_R_jnt', 12: 'TE_R_jnt',
                 13: 'SAKOTSU_L_jnt', 14: 'KATA_L_jnt', 15: 'UDE_L_jnt', 16: 'TE_L_jnt',
                 17: 'MOMO_R_jnt', 18: 'HIZA_R_jnt', 19: 'ASHI_R_jnt', 20: 'MOMO_L_jnt', 21: 'HIZA_L_jnt',
                 22: 'ASHI_L_jnt'}


def bone_index(bon):
    return {n[4:] if n.startswith('cha:') else n: i for i, n in enumerate(bon['names'])}


def world(bon, local_rotations, root_position):
    """World matrices (n, 4, 4): local_rotations {bone index: 3x3}, root_position (3,) for bone 0."""
    n = len(bon['parent'])
    w = np.zeros((n, 4, 4))
    for i in range(n):
        m = bone.local_matrix(bon, i)
        if i in local_rotations:
            m[:3, :3] = local_rotations[i]
        if i == 0:
            m[:3, 3] = root_position
        p = bon['parent'][i]
        w[i] = m if p < 0 else w[p] @ m
    return w

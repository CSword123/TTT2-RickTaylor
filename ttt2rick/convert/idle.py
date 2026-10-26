"""Rick's own fighting stance (Splatterhouse's combatidle) and guard (block) as TTT2 animations, in his own motion pack.

python -m ttt2rick.convert.idle <game folder> <Splatterhouse data folder> <converted Rick (convert.rick's out)> <out dir>

1. The Havok animation (ttt2rick.splatterhouse.hkx) gives each of Rick's joints' world transform per frame G_J(f),
   and the reference pose G_J(ref), which is the bind pose his mesh was made from.
2. ttt2rick.convert.rick turned his joints to the donor's T-pose directions (repose: world deltas D_J) before skinning
   his mesh to the TTT2 skeleton. So the mesh near joint J, posed as in frame f, is G_J(f) G_J(ref)^-1 D_J^-1 applied
   to the TTT2 bind mesh, and the TTT2 bone T that J's skin went to needs the world rotation
       W_T(f) = R(G_J(f)) R(G_J(ref))^-1 R(D_J)^-1 R(W_T(bind)).
   Each animated TTT2 bone takes it from one joint (DRIVERS); its local rotation is its parent's animated world
   inverse times that, top-down (ttt2rick.ttt2.fk), as the Euler angles of a raw (0xC8) animation.
3. The model root (channel 1) is its bind place under G_J(f) G_J(ref)^-1 D_J^-1 of Rick's root joint, as the mesh
   around it is (D_J with ttt2rick.convert.rick's lift, which stood the straightened legs on the floor: his own bent
   legs need it taken off again, or his soles float ~10 cm), divided by the skeleton's scale (the game multiplies
   channel 1 by it: checked on Marduk's stance, whose feet then stand on the floor). His feet then stand as in
   Splatterhouse: soles on the floor, ankles 156 mm up.
   The ground displacement, turn and spine parameter (channels 0, 2, 6) are Marduk's stance's first frame.
4. Frames: Havok's 30 a second, sampled at TTT2's 60.
Out: files/key_<RICK_MOTIONS>.bin, Marduk's motion pack with the standing animation (body animation STAND_ANIM,
which Marduk's standing move Va_sKAM00_ plays as 0x4026) replaced by Rick's, his guard appended (GUARD_ANIM, which
ttt2rick.convert.slot gives his standing guard moves) and his attacks in place of Marduk's (ttt2rick.convert.attacks),
for his own motion row (rick_slot.cpp kRow, kRickMotions); and idle_preview.png / guard_preview.png /
attack_<index>_preview.png (Havok's pose and the TTT2 skeleton's, side by side).
"""
import json
import os
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw

from ..splatterhouse import extract, hkx
from ..ttt2 import fk, xbox
from ..ttt2.archive import Archives
from ..ttt2.petexy import animation, bone, motion
from . import attacks
from . import rick as rickconv

RICK_NIF_DIR = 'characters/rick_havok/xbox360'
IDLE = 'combatidle.hkx'
GUARD = 'block.hkx'              # his held block: the animation of his standing guards (ttt2rick.convert.slot)
# Splatterhouse's stance has his right side forward (shoulders 29 degrees that way), so player 1 showed his back and
# player 2 his front, the other way round from TTT2's fighters (Marduk: left side forward, hips 55 degrees). Every
# animation is turned STANCE_TURN more about the vertical (his attacks too, from the stance's turn), mirroring
# that: hips about 58 degrees left side forward, as Marduk's.
STANCE_TURN = np.radians(58.0)
GUARD_FRAMES = 40                # at FPS; Marduk's standing guards go back to the stance at their frame 19
GUARD_ANIM = 684                 # the guard's body animation, after Marduk's 684: moves play it as 0x4000 + 684
MARDUK_MOTIONS = 0xC903BD27      # motion row 17's motion pack (684 animations; 0x75F7BE7E is row 18's, Jack-6)
RICK_MOTIONS = 0x52494332        # "RIC2": rick_slot.cpp kRickMotions
STAND_ANIM = 0x26                # Marduk's standing animation (body MOTA index; his moves name it 0x4026)
FPS = 60.0
# TTT2 bone (channel) -> the Rick joint whose rotation it takes. The chest channel (MUNE1, which the game spreads
# over MUNE1 and MUNE2) takes the upper torso's: his hunch bends there (20 degrees in combatidle), and with the mid
# torso's the chest stayed upright under a hunched neck and head, the skin between them stretched into a sheet.
DRIVERS = {'HARA_ROT1': 'root_jnt', 'KOSHI_jnt': 'root_jnt', 'MUNE1_jnt': 'C_upperTorso_jnt',
           'KUBI_jnt': 'C_neck_01_jnt', 'ATAMA_jnt': 'C_head_01_jnt'}
for _s in 'RL':
    DRIVERS.update({'SAKOTSU_%s_jnt' % _s: '%s_clavicle_02_jnt' % _s, 'KATA_%s_jnt' % _s: '%s_shoulder_jnt' % _s,
                    'UDE_%s_jnt' % _s: '%s_elbow_jnt' % _s, 'TE_%s_jnt' % _s: '%s_wrist_jnt' % _s,
                    'MOMO_%s_jnt' % _s: '%s_upperLeg_jnt' % _s, 'HIZA_%s_jnt' % _s: '%s_lowerLeg_jnt' % _s,
                    'ASHI_%s_jnt' % _s: '%s_ankle_jnt' % _s})


def quat_matrix(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def havok_worlds(sk, locals_):
    """World 4x4s in TTT2 space (mm) of the Havok joints for one set of local transforms (n, 10)."""
    n = len(sk['names'])
    g = [None] * n
    for i in range(n):
        m = np.eye(4)
        m[:3, :3] = quat_matrix(locals_[i, 3:7])
        m[:3, 3] = locals_[i, 0:3]
        g[i] = m if sk['parents'][i] < 0 else g[sk['parents'][i]] @ m
    out = np.zeros((n, 4, 4))
    for i in range(n):
        out[i] = np.eye(4)
        out[i][:3, :3] = extract.SWAP @ g[i][:3, :3] @ extract.SWAP.T
        out[i][:3, 3] = extract.to_ttt2_points(g[i][:3, 3][None])[0]
    return out


def sample(an, sk, fps, times=None):
    """Per output frame, the Havok local transforms (n joints, 10) at fps, or at `times` (Havok frame numbers, one
    per output frame: a retimed animation): tracks interpolated (positions linearly, rotations by normalized lerp in
    one hemisphere) between Havok's frames."""
    tracks, src_fps = an['tracks'], an['fps']
    if times is None:
        times = np.arange(max(1, int(round((an['frames'] - 1) * fps / src_fps)) + 1)) * src_fps / fps
    count = len(times)
    out = np.tile(sk['reference'][None], (count, 1, 1)).astype(float)
    for k in range(count):
        t = min(max(times[k], 0.0), an['frames'] - 1)
        a = int(np.floor(t))
        b = min(a + 1, an['frames'] - 1)
        u = t - a
        for tr, j in enumerate(an['bones']):
            pa, pb = tracks[a, tr], tracks[b, tr]
            qb = pb[3:7] if np.dot(pa[3:7], pb[3:7]) >= 0 else -pb[3:7]
            q = pa[3:7] * (1 - u) + qb * u
            out[k, j, 0:3] = pa[0:3] * (1 - u) + pb[0:3] * u
            out[k, j, 3:7] = q / np.linalg.norm(q)
    return out


def blend_in(local, start, n):
    """local (frames, joints, 10) with its first n frames blended from the pose `start` (joints, 10), smoothly:
    positions linearly, rotations by normalized lerp in one hemisphere."""
    out = local.copy()
    for f in range(min(n, len(local))):
        u = f / n
        u = u * u * (3 - 2 * u)
        a, b = start, local[f]
        q = np.where((np.einsum('ji,ji->j', a[:, 3:7], b[:, 3:7]) < 0)[:, None], -b[:, 3:7], b[:, 3:7])
        out[f, :, 0:3] = a[:, 0:3] * (1 - u) + b[:, 0:3] * u
        q = a[:, 3:7] * (1 - u) + q * u
        out[f, :, 3:7] = q / np.linalg.norm(q, axis=1, keepdims=True)
    return out


def preview(frames_h, names_h, parents_h, frames_t, parents_t, path):
    """Stick figures, front and side, of a few frames: Havok's joints (left) and the TTT2 skeleton (right)."""
    picks = np.linspace(0, len(frames_h) - 1, 4).astype(int)
    img = Image.new('RGB', (4 * 2 * 220, 2 * 300), (30, 30, 34))
    d = ImageDraw.Draw(img)
    for c, f in enumerate(picks):
        for side, (pts, par, col) in enumerate(((frames_h[f], parents_h, (240, 200, 90)),
                                                (frames_t[f], parents_t, (120, 200, 250)))):
            for view in (0, 1):
                ox, oy = (2 * c + side) * 220 + 110, view * 300 + 285
                for i, p in enumerate(par):
                    if p < 0:
                        continue
                    a, b = pts[i], pts[p]
                    ax, bx = (a[0], b[0]) if view == 0 else (a[2], b[2])
                    d.line([(ox + ax * 0.11, oy - a[1] * 0.11), (ox + bx * 0.11, oy - b[1] * 0.11)], fill=col, width=2)
    img.save(path)


class Retarget:
    """What every animation's retarget needs: Rick's Havok skeleton and reference pose, the repose deltas
    ttt2rick.convert.rick made, his TTT2 skeleton, and Marduk's stance (its descriptors and constant channels)."""

    def __init__(self, arc, folder, rick_out):
        self.folder = folder
        self.sk = hkx.skeleton(hkx.Packfile(open(os.path.join(folder, 'rick_skeleton.hkx'), 'rb').read()))
        self.hidx = {n: i for i, n in enumerate(self.sk['names'])}
        self.Gref = havok_worlds(self.sk, self.sk['reference'])
        rick_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(rick_out))), 'rick', 'brawler')
        info = json.load(open(os.path.join(rick_dir, 'model.json')))
        data = np.load(os.path.join(rick_dir, 'model.npz'))
        names, parents = info['skeleton']['names'], info['skeleton']['parents']
        donor = xbox.read_bone(arc.read_name(rickconv.DONOR + '.bon'))
        dW = bone.world_matrices(donor)
        dnames = [n[4:] if n.startswith('cha:') else n for n in donor['names']]
        self.D = rickconv.reposed(names, parents, data['skeleton_world'][:, :3, 3].astype(np.float64),
                                  {n: dW[i][:3, 3] for i, n in enumerate(dnames)}, info, data)
        self.nidx = {n: i for i, n in enumerate(names)}
        self.bon = xbox.read_bone(open(os.path.join(rick_out, 'files', rickconv.DONOR + '.bon'), 'rb').read())
        self.stand = marduk_stand(arc)
        self.yaws = {}

    def __call__(self, name, frames=None, times=None, yaw=None, blend_from=None, ground=None):
        """(raw animation, Havok joint positions per frame, TTT2 joint positions per frame) of Rick's Havok
        animation `name`, its first `frames` frames at FPS (all by default), or sampled at `times` (Havok frames).
        yaw: the root turn to take out (radians; default the animation's mean, kept in self.yaws[name]), or one per
        frame (an attack turned toward its target).
        blend_from: (Havok local pose, n): the first n frames blend from that pose into the animation.
        ground: (frames, 3) added to channel 0, the ground displacement (z forward: a move's travel)."""
        sk, hidx, Gref, D, nidx, bon = self.sk, self.hidx, self.Gref, self.D, self.nidx, self.bon
        an = hkx.animation(hkx.Packfile(open(os.path.join(self.folder, name), 'rb').read()))
        local = sample(an, sk, FPS, times)[:frames]
        if blend_from is not None:
            local = blend_in(local, *blend_from)
        G = np.array([havok_worlds(sk, f) for f in local])
        bi = fk.bone_index(bon)
        Wbind = fk.world(bon, {}, bon['t'][0])
        scale = float(bon['scale'])
        desc = self.stand['descriptors']
        values = np.zeros((len(local), len(desc), 3))
        chan_of = {bi[b]: c for c, b in fk.CHANNEL_BONES.items()}
        root_j = hidx[DRIVERS['HARA_ROT1']]
        # Havok's root faces its own way in the animation: its mean turn about the vertical (from the reference) is
        # taken out, so Rick faces his opponent as the TTT2 skeleton does
        fwd = np.array([G[f, root_j, :3, :3] @ Gref[root_j, :3, :3].T @ [0, 0, 1] for f in range(len(local))])
        if yaw is None:
            yaw = np.arctan2(fwd.mean(0)[0], fwd.mean(0)[2]) + STANCE_TURN
        yaws = np.broadcast_to(np.asarray(yaw, float), (len(local),))
        self.yaws[name] = float(np.mean(yaws))
        self.first_yaw = np.arctan2(fwd[0][0], fwd[0][2])
        c, s_ = np.cos(-yaws), np.sin(-yaws)
        Y = np.zeros((len(local), 3, 3))
        Y[:, 0, 0], Y[:, 0, 2], Y[:, 1, 1], Y[:, 2, 0], Y[:, 2, 2] = c, s_, 1, -s_, c
        G = G.copy()
        G[:, :, :3, :3] = np.einsum('fij,fnjk->fnik', Y, G[:, :, :3, :3])
        G[:, :, :3, 3] = np.einsum('fij,fnj->fni', Y, G[:, :, :3, 3] - Gref[root_j, :3, 3]) + Gref[root_j, :3, 3]
        print('%s: root turn taken out: %.1f degrees' % (name, np.degrees(np.mean(yaws))))
        tposes = []
        for f in range(len(local)):
            target = {}
            for c, b in fk.CHANNEL_BONES.items():
                j = DRIVERS[b]
                R = G[f, hidx[j], :3, :3] @ Gref[hidx[j], :3, :3].T @ D[nidx[j], :3, :3].T @ Wbind[bi[b], :3, :3]
                target[bi[b]] = R
            # the root moves with the mesh around it: G(f) G(ref)^-1 D^-1 on its bind place, D with convert.rick's
            # lift (which stood the straightened legs on the floor: Havok's bent legs need it taken off again)
            M = G[f, root_j] @ np.linalg.inv(Gref[root_j]) @ np.linalg.inv(D[nidx[DRIVERS['HARA_ROT1']]])
            root = M[:3, :3] @ bon['t'][0] + M[:3, 3]
            # top-down: each animated bone's local rotation under its parent's animated world
            n = len(bon['parent'])
            w = np.zeros((n, 4, 4))
            rots = {}
            for i in range(n):
                m = bone.local_matrix(bon, i)
                if i == 0:
                    m[:3, 3] = root
                p = bon['parent'][i]
                pw = np.eye(4) if p < 0 else w[p]
                if i in target:
                    m[:3, :3] = pw[:3, :3].T @ target[i]
                    rots[i] = m[:3, :3]
                w[i] = pw @ m
            tposes.append(w[:, :3, 3].copy())
            values[f] = self.stand['values'][0]
            for i, R in rots.items():
                values[f, chan_of[i]] = bone.euler_xyz_from_matrix(R)
            values[f, 1] = root / scale * np.array([1, 1, -1])
            if ground is not None:
                values[f, 0] += ground[f]
        return raw_animation(desc, values), [g[:, :3, 3] for g in G], tposes


def main(game, splatter, rick_out, out):
    arc = Archives(game)
    folder = os.path.join(splatter, RICK_NIF_DIR) if os.path.isdir(os.path.join(splatter, RICK_NIF_DIR)) else splatter
    retarget = Retarget(arc, folder, rick_out)
    stance, hp, tp = retarget(IDLE)
    guard, ghp, gtp = retarget(GUARD, GUARD_FRAMES)
    pack = with_animation(arc.read(MARDUK_MOTIONS), STAND_ANIM, stance)
    pack, index = with_appended(pack, guard)
    if index != GUARD_ANIM:
        raise ValueError('the guard went to body animation %d, not GUARD_ANIM %d' % (index, GUARD_ANIM))
    pack, shown = attacks.with_attacks(pack, retarget, IDLE)
    pack, more = attacks.with_new_attacks(pack, retarget, IDLE)
    shown.update(more)
    os.makedirs(os.path.join(out, 'files'), exist_ok=True)
    open(os.path.join(out, 'files', 'key_%08x.bin' % RICK_MOTIONS), 'wb').write(pack)
    names, parents = retarget.sk['names'], retarget.sk['parents']
    preview(hp, names, parents, tp, retarget.bon['parent'], os.path.join(out, 'idle_preview.png'))
    preview(ghp, names, parents, gtp, retarget.bon['parent'], os.path.join(out, 'guard_preview.png'))
    for index, (ahp, atp) in shown.items():
        preview(ahp, names, parents, atp, retarget.bon['parent'], os.path.join(out, 'attack_%x_preview.png' % index))
    print('%s: stance %d frames, guard %d frames (body animation %d = %#x) at %.0f fps, motion pack %d bytes' % (
        out, len(hp), len(ghp), GUARD_ANIM, 0x4000 + GUARD_ANIM, FPS, len(pack)))


def marduk_stand(arc):
    pack = arc.read(MARDUK_MOTIONS)
    o0, offs = mota(pack)
    return animation.decode(pack, '>', o0 + offs[STAND_ANIM])


def mota(pack):
    """(MOTA offset in the pack, [animation offsets from the MOTA]) of the pack's body MOTA (item 0)."""
    o0 = struct.unpack_from('<I', pack, 4)[0]
    if pack[o0:o0 + 4] != b'MOTA':
        raise ValueError('motion pack item 0 is not a MOTA')
    cnt = struct.unpack_from('>I', pack, o0 + 0xC)[0]
    return o0, list(struct.unpack_from('>%dI' % cnt, pack, o0 + 0x14))


def raw_animation(descriptors, values):
    return animation.encode_raw(descriptors, values, '>')


def with_animation(pack, index, anim):
    """The motion pack with body animation `index` replaced: the new one appended to the body MOTA (16-byte
    aligned) and its offset pointed at it; the pack's items rebuilt."""
    n = struct.unpack_from('<I', pack, 0)[0]
    items = [pack[o:o + s] for o, s in (struct.unpack_from('<II', pack, 4 + 8 * k) for k in range(n))]
    body = bytearray(items[0])
    body += bytes(-len(body) % 16)
    struct.pack_into('>I', body, 0x14 + 4 * index, len(body))
    body += anim
    items[0] = bytes(body)
    out = bytearray(0x40)
    struct.pack_into('<I', out, 0, n)
    for k, it in enumerate(items):
        out += bytes(-len(out) % 16)
        struct.pack_into('<II', out, 4 + 8 * k, len(out), len(it))
        out += it
    return bytes(out)



def with_appended(pack, anim):
    """(the motion pack with `anim` appended to its body MOTA, the new animation's index)."""
    items = [pack[o:o + s] for o, s in motion.pack_items(pack)]
    index = len(motion.mota_offsets(items[0])[1])
    items[0] = motion.extend_mota(items[0], [anim])
    return motion.build_pack(items), index

if __name__ == '__main__':
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    main(*sys.argv[1:])

"""Rick's voice: Josh Keaton's grunts from Splatterhouse in a sound bank of his own, se_Chr_ric (Marduk's se_Chr_mar
with every shout, damage voice and KO scream replaced).

python -m ttt2rick.convert.voice <game folder> <Splatterhouse data folder> <out dir>
Writes <out>/files/se_Chr_ric.nus3bank (for ttt2rick.ttt2.overlay) and <out>/<tone>.wav, each clip as the bank has it.

Splatterhouse's voice bank (sounds/soundbanks/xbox360/English(US)/sb_rick_vox.bnk, an XMemCompress'd Wwise bank)
holds his clips as Wwise media (DIDX/DATA chunks): RIFX (big-endian) files of XMA2 audio, mono, 24 or 32 kHz. Their names
are in the soundbanks' index (SoundbanksInfo.xml, compressed too): `newPunches` (his punch grunts), `lastSwing` (a
combo's last swing), `knockback` light/medium/heavy (being hit), `exerts`. TTT2's tones (NUS3BANK, ttt2rick.ttt2.petexy
.nus3bank) hold little-endian RIFF files of the same XMA2 audio (Marduk's: mono, 44.1 kHz): {fmt (XMA2WAVEFORMATEX,
52 bytes), seek (big-endian sample counts per block, as XMA has them), data}. So each clip is not re-encoded: its
XMA2 packets go into a RIFF of its own header's fields, byte-swapped, and the tone's trailing format fields
{rate, channels, data size / 2} are set to them.

Marduk's se_Chr tones by kind (CLIPS; his voice list plays them by category: shouts 0x21 short, 0x22 medium, 0x20
long, 0x44 / 0x48 small and big damage, 0x90 KO): each gets the Splatterhouse clip of that kind closest in length.
Splatterhouse's clips are quieter (RMS -17 to -24 dB against Marduk's -11 to -18), so each tone's gain (the f32 after
its PACK place, in dB: Marduk's are -3 to +2) is moved by the difference in RMS, at most MAX_GAIN.

The bank is named se_Chr_ric with its own id in the sound project (BINF: PROJECT_ID; the sound library refuses a
bank whose id a loaded bank has, as Petexy's Wii U port found). recomp/runtime/rick_voice.cpp gives Rick the game's
bank id RICK_BANK (one the title leaves free), whose key is this file's, and sound ids of his own that play its
tones.
"""
import os
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET

import numpy as np

from ..common import xlzx
from ..ttt2.archive import Archives
from ..ttt2.petexy.nus3bank import Bank

DONOR_BANK = 'se_Chr_mar.nus3bank'
BANK = 'se_Chr_ric'
PROJECT_ID = 1000                # BINF id; Marduk's se_Chr is 29, the title's go up to the 400s
RICK_BANK = 1                    # the game's bank id (rick_voice.cpp kRickBank: free in sub_825A6010's switch)
VOX = 'sounds/soundbanks/xbox360/English(US)/sb_rick_vox.bnk'
INDEX = 'sounds/soundbanks/xbox360/SoundbanksInfo.xml'
MAX_GAIN = 9.0
# Marduk's tone -> Splatterhouse's clip (its file name in the bank's index)
CLIPS = {
    '_s_mar_atck_s01': 'vox_rick_newPunch_09',        # short shouts: jabs and quick punches
    '_s_mar_atck_s02': 'vox_rick_newPunch_12',
    '_s_mar_atck_s03': 'vox_rick_newPunch_10',
    '_s_mar_atck_m01': 'vox_rick_newPunch_11',        # medium: heavier punches
    '_s_mar_atck_m02': 'vox_rick_newPunch_16',
    '_s_mar_atck_m03': 'vox_rick_newPunch_08',
    '_s_mar_atck_l01': 'vox_rick_lastSwing_03',       # long: finishers, throws
    '_s_mar_atck_l02': 'vox_rick_lastSwing_06',
    '_s_mar_atck_l03': 'b_rick_exert_4',
    '_s_mar_dmg_s01': 'B-RICK-CMBT-KB-03_c',          # small damage: light knockbacks
    '_s_mar_dmg_s02': 'B-RICK-CMBT-KB-04_a',
    '_s_mar_dmg_s03': 'B-RICK-CMBT-KB-03_b',
    '_s_mar_dmg_l01': 'B-RICK-CMBT-KB-07_c',          # big damage: medium knockbacks
    '_s_mar_dmg_l02': 'B-RICK-CMBT-KB-08_a',
    '_s_mar_dmg_l03': 'B-RICK-CMBT-KB-04_c',
    '_s_mar_dmg_l04': 'B-RICK-CMBT-KB-04_d',
    '_s_mar_dmg_ko01': 'B-RICK-CMBT-DEATH-15_b',      # KO: heavy knockbacks
    '_s_mar_dmg_ko02': 'B-RICK-CMBT-DEATH-13_f',
}
XMA2 = '<HHIIHHHHIIIIIIIBBH'     # XMA2WAVEFORMATEX: tag .. cbSize, streams, mask, samples encoded, bytes per block,
                                 # play begin/length, loop begin/length/count, encoder version, block count


def riff_chunks(d, endian):
    """{tag: data} of a RIFF ('<') or RIFX ('>') file."""
    out, p = {}, 12
    while p + 8 <= len(d):
        n, = struct.unpack_from(endian + 'I', d, p + 4)
        out[d[p:p + 4]] = d[p + 8:p + 8 + n]
        p += 8 + n + (n & 1)
    return out


def media(splatter):
    """{clip name: Wwise media bytes} of Rick's voice bank."""
    bank = xlzx.read_file(open(os.path.join(splatter, VOX), 'rb').read())
    index = xlzx.read_file(open(os.path.join(splatter, INDEX), 'rb').read()).decode('utf-8-sig')
    names = {}
    for b in ET.fromstring(index).iter('SoundBank'):
        if (b.findtext('ShortName') or '').lower() == 'sb_rick_vox':
            for f in b.iter('File'):
                if f.findtext('ShortName'):
                    names[int(f.get('Id'))] = os.path.splitext(f.findtext('ShortName').split('\\')[-1])[0]
    chunks, p = {}, 0
    while p < len(bank):
        n, = struct.unpack_from('>I', bank, p + 4)
        chunks[bank[p:p + 4]] = (p + 8, n)
        p += 8 + n
    (didx, count), (data, _) = chunks[b'DIDX'], chunks[b'DATA']
    out = {}
    for k in range(count // 12):
        i, off, size = struct.unpack_from('>III', bank, didx + 12 * k)
        if i in names:
            out[names[i]] = bank[data + off:data + off + size]
    return out


def riff(wem):
    """A Wwise RIFX XMA2 file as TTT2's RIFF -> (bytes, sample rate, channels, data size, samples played)."""
    c = riff_chunks(wem, '>')
    fmt = struct.unpack('>' + XMA2[1:], c[b'fmt '][:52])
    if fmt[0] != 0x166:
        raise ValueError('not XMA2 (format %#x)' % fmt[0])
    body = b'WAVE' + b''.join(tag + struct.pack('<I', len(v)) + v for tag, v in (
        (b'fmt ', struct.pack(XMA2, *fmt)), (b'seek', c[b'seek']), (b'data', c[b'data'])))
    return b'RIFF' + struct.pack('<I', len(body)) + body, fmt[2], fmt[1], len(c[b'data']), fmt[12]


def rms_db(audio, path):
    """RMS level (dBFS) of a RIFF XMA2 clip, decoded by ffmpeg (written to path to look at)."""
    open(path, 'wb').write(audio)
    pcm = subprocess.run(['ffmpeg', '-v', 'quiet', '-i', path, '-f', 's16le', '-ac', '1', '-'],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(pcm, '<i2').astype(float)
    return 20 * np.log10(max(1.0, np.sqrt((a * a).mean())) / 32768)


def main(game, splatter, out):
    arc = Archives(game)
    bank = Bank(arc.read_name(DONOR_BANK))
    clips = media(splatter)
    os.makedirs(os.path.join(out, 'files'), exist_ok=True)
    tones = {bank.name(i): i for i in range(len(bank.tones))}
    for tone, clip in CLIPS.items():
        i = tones[tone]
        audio, rate, channels, size, played = riff(clips[clip])
        name = tone.replace('_mar_', '_ric_')
        level = rms_db(bank.audio[i], os.path.join(out, tone + '.wav'))
        mine = rms_db(audio, os.path.join(out, name + '.wav'))
        at = Bank._fields(bank.tones[i]) + 16
        gain, = struct.unpack_from('<f', bank.tones[i], at)
        new = min(MAX_GAIN, gain + level - mine)
        bank.replace(i, audio, rate, channels, size // 2)
        struct.pack_into('<f', bank.tones[i], at, new)
        bank.tones[i] = bank.renamed(i, name)
        print('%s <- %s: %.2f s, %d Hz, gain %+.1f dB (Marduk\'s %+.1f; RMS %.1f against his %.1f)' % (
            name, clip, played / rate, rate, new, gain, mine, level))
    bank.rename(BANK, PROJECT_ID)
    data = bank.write()
    open(os.path.join(out, 'files', BANK + '.nus3bank'), 'wb').write(data)
    print('%s: %d bytes (Marduk\'s %d), bank id %d in the game, %d in the sound project' % (
        BANK, len(data), len(arc.read_name(DONOR_BANK)), RICK_BANK, PROJECT_ID))


if __name__ == '__main__':
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])

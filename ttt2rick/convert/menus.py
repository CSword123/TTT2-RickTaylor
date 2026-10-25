"""Rick in the menus that are scripts: TTT2's menu definitions (BX01 files) carry Xtal script source, which the game
compiles when it loads them, so editing the text changes the menu.

The title update's menu file MENU_KEY defines `global::CharacterSelectCursor`, the character grid of Customize (and of
the other screens that use the class: replay search, ending movie select): GetFighterID(x, y) reads a 3 x 22 table
`chr_line` (row 0 the top row, its x 3..17 the fighters Uju..Violet, the rest ID_PRA, empty) and
IsFocusableCharacter(x, y) refuses the top row's x 0-2 and 18-21. Rick's panel is right of Violet (x 18), so his id
goes there, x 18 is let in, and his cell skips lib::MNcheckFighterRelease (the unlock test, which knows ids 0-62).
The edits keep every length (the container's offsets stay right): text is replaced by text of the same length,
padded with spaces.

Status (2026-10-25): with these edits the Customize cursor reaches Rick's cell, but choosing him starts his costume
panel's load (sub_8272A5F0, a two-slot loader), which never finishes, and the menu stops taking input. So
ttt2rick.convert.slot ships them only with RICK_CUSTOMIZE=1, until his costume data (item database, save entry) is
there.
"""
MENU_KEY = 0xB43EB78F            # title update (data100) menu file with CharacterSelectCursor
RICK_ID = 64                     # rick_slot.cpp kId

EDITS = [
    # the top row's refused columns: 18-21 -> 19-21
    (b'( x >= 18 && x <= 21 )', b'( x >= 19 && x <= 21 )'),
    # Rick's cell skips the unlock test
    (b'if ( lib::MNcheckFighterRelease( GetFighterID( x, y ) ) ) {',
     b'if ( x == 18 || lib::MNcheckFighterRelease( GetFighterID( x, y ) ) ) {'),
    # chr_line row 0, x 18: Rick
    (b'lib::ID_VIO, lib::ID_PRA,', b'lib::ID_VIO, %-11d,' % RICK_ID),
]


def edit(data):
    """The menu file with EDITS made; each must be found exactly once. Length changes are taken from the comment
    padding of the same line, so the file keeps its size."""
    out = bytearray(data)
    for old, new in EDITS:
        if out.count(old) != 1:
            raise ValueError('menu edit: %r found %d times' % (old, out.count(old)))
        at = out.index(old)
        grow = len(new) - len(old)
        if grow > 0:
            # take the extra length from the run of spaces that indents the next line
            end = out.index(b'\r\n', at + len(old))
            pad = end + 2
            while out[pad:pad + 1] == b' ' and pad - (end + 2) < grow:
                pad += 1
            if pad - (end + 2) < grow:
                raise ValueError('menu edit: no room after %r' % old)
            del out[end + 2:end + 2 + grow]
        out[at:at + len(old)] = new
    if len(out) != len(data):
        raise ValueError('menu edit changed the size: %d -> %d' % (len(data), len(out)))
    return bytes(out)


def files(arc):
    """{overlay file name: bytes} of the edited menus."""
    idx = arc.indices['update/data100.bin']
    i = next(k for k, e in enumerate(idx) if e[0] == MENU_KEY)
    return {'key_%08x.bin' % MENU_KEY: edit(arc.entry('update/data100.bin', i))}

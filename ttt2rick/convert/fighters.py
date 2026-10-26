"""The added fighters, as the picture converters (ttt2rick.convert.portrait, hud, layouts) make their pictures: one
run makes every added fighter's pictures, since they share the title's containers (the select portraits', the HUD's,
each layout's), which the overlay replaces whole. The numbers here are recomp/runtime/rick_slot.cpp's kFighters'.

Per fighter:
- code, name: its code (labels `chara_face_<code>`, files `<code>/portrait_1p.nut`) and its name in capitals;
- picture: work/art/<...>.png (ttt2rick.convert.picture.load), and whether its blood is cleaned off (Rick's portraits;
  each is then also made with the blood, `_blood`);
- face: in the picture, the eyes' centre (x, y) and the eyes-to-chin distance (layouts: Layout's pictures), and
  icon: where the face goes in the select grid's 56 x 88 icons (eyes x, y and eyes-to-chin as fractions of the icon);
- hud_face: (scale of the picture, the head's middle x, its top y) for the fights' 140 x 140 face;
- portrait: (scale of the picture, the picture's x put at the portrait's middle, its y put at the portrait's top
  margin) for the big select portraits (356 x 612), and how many of the picture's pixels its edge is trimmed by
  there (portrait_fringe: Rick's picture has a dark cut-out edge);
- portrait_frame: its first frame in the select portraits' container (player 1, player 2; the bloody two after);
- hud: its three numbers in the HUD container (name, face of player 1, face of player 2), and hud_letters: its
  name's letters as (UI row of a HUD name that has it, its core's columns in that name's texture);
- cell: its select grid cell in the layouts (above `anchor`'s panel, in the top row): rick_slot.cpp's column.
"""
import os

from .clean import clean_picture

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')


class Fighter:
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def picture_path(self):
        return os.path.join(ROOT, 'work', 'art', self.picture)

    def variants(self, picture):
        """[(picture, file suffix)]: the clean picture, and the bloody one when its blood is cleaned off."""
        return [(clean_picture(picture), ''), (picture, '_blood')] if self.clean else [(picture, '')]


RICK = Fighter(code='ric', name='RICK', picture='rick_taylor.png', clean=True,
               face=(466, 134, 98), icon=(0.50, 0.40, 0.30), hud_face=(0.46, 462, 0), portrait=(0.70, 459, 0), portrait_fringe=5,
               portrait_frame=118, hud=(259, 260, 261), cell={'anchor': 'edd', 'columns': 0, 'grid_row': 0},
               hud_letters=[(18, 74, 97), (9, 34, 40), (27, 97, 121), (18, 154, 179)])   # MARDUK JIN BRUCE MARDUK
JEN = Fighter(code='jen', name='JENNIFER', picture='jennifer_willis.png', clean=False,
              face=(536, 92, 41), icon=(0.48, 0.36, 0.20), hud_face=(0.64, 532, 28), portrait=(1.12, 522, 28), portrait_fringe=1,
              portrait_frame=122, hud=(262, 263, 264), cell={'anchor': 'lee', 'columns': 0, 'grid_row': 0},
              hud_letters=[(9, 12, 30), (31, 38, 59), (31, 62, 88), (31, 62, 88), (9, 34, 40), (31, 16, 37),
                           (31, 38, 59), (18, 74, 97)])         # JIN FENG FENG FENG JIN FENG FENG MARDUK
ADDED = [RICK, JEN]

This is a 99% vibe coded mod for Calikid/shihabal3amri's Tekken Tag Tournament 2 recomp intended for Windows/Linux. It adds Rick Taylor and/or Jennifer Willis from Splatterhouse 2010 as playable characters. If it bothers you that AI was used in the creation of this or you don't like that some bugs are present, do NOT try this mod. Otherwise, it is available on the Releases page and you can either submit a bug report as an issue on Github or use the source documentation and code available to work on a better version yourself.

What you NEED:
1. Python installed in Windows or Linux. make sure you are able to install packages using pip as you need numpy and Pillow (read install.py for more info).
2. ffmpeg (make sure python is set in your system PATH to invoke them in powershell or command line in windows)
3. A Splatterhouse Xbox 360 USA ISO (please make an effort to use your own copy) and one of the aformentioned recomp's installed.
   
What you DO:
1. run the installer script (install.py) in a command line
Example: $ python install.py
If you need numpy or Pillow run "pip install -r requirements.txt"
You can edit the resulting .ini file for things like "Rick only" and enabling original blood textures on Rick in the directory where your recomp is installed

Rick and Jen are based on Marduk's moveset with Splatterhouse 2010 moves sprinkled in. f+2,1,1, f+2,2,1,2 and b+2,1,1+2 are based on Rick's 2010 melee attacks among other animations.
Customization for Rick is a goal but currently WIP.

Why Rick/Jen in TTT2? To simply fulfill a dream of mine and for fun. I do not own the Splatterhouse IP nor Tekken so if a Bandai Namcop is reading this for the purpose of taking down recomp mods, please understand that I just want Rick Taylor in a Tekken game and i would purchase future official Tekken content with him in it.

https://github.com/thatcalikid760/TTT2-Recomp
https://github.com/shihabal3amri/tekken-tag-tournament-2-pc

This Splatterhouse project was used to get Rick and Jen working for the mod:
https://github.com/0c0de/splatterhouse-decomp
And portions of Petexy's Wii U recomp was used to get Rick imported to 360 Tag 2:
https://github.com/Petexy/Tekken-Tag-2-Ultimate-Edition

Future goals:
  1. get stock Customization for Rick working
  2. bug fixes
  3. possibly integrating with Petexy's Wii U recomp

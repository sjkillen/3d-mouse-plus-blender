from glob import glob
from shutil import move

for i, image in enumerate(sorted(glob("images/*.png"))):
    move(image, f"images/{i:04}.png")
import ndspy.rom
import ndspy.soundArchive
import ndspy.soundWaveArchive
import sys
from PIL import Image
import struct


def image_to_ds_icon(image_path):
    img = Image.open(image_path).convert('RGB').resize((32, 32))
    img = img.quantize(colors=15)  # index 0 is reserved for transparency
    palette_data = img.getpalette()
    pixels = list(img.getdata())

    # DS palette is BGR555 - 2 bytes per colour, 16 colours total
    palette_bytes = bytearray(32)
    for i in range(15):
        r = palette_data[i*3] >> 3
        g = palette_data[i*3+1] >> 3
        b = palette_data[i*3+2] >> 3
        colour = (b << 10) | (g << 5) | r
        struct.pack_into('<H', palette_bytes, (i+1)*2, colour)

    # Icon is stored as 4x4 grid of 8x8 tiles, 4bpp
    tile_bytes = bytearray(512)
    for tile_y in range(4):
        for tile_x in range(4):
            for y in range(8):
                for x in range(0, 8, 2):
                    px = tile_x*8 + x
                    py = tile_y*8 + y
                    p1 = pixels[py*32 + px] + 1
                    p2 = pixels[py*32 + px + 1] + 1
                    byte_pos = (tile_y*4 + tile_x)*32 + y*4 + x//2
                    tile_bytes[byte_pos] = (p2 << 4) | p1

    return tile_bytes, palette_bytes


def set_ds_title(banner, language_index, title):
    # Titles start at offset 576, 256 bytes each (UTF-16LE)
    offset = 576 + language_index * 256
    encoded = title.encode('utf-16-le')
    encoded = encoded[:254] + b'\x00\x00'
    banner[offset:offset+len(encoded)] = encoded


def update_icon_banner(banner, image_path, title):
    tile_bytes, palette_bytes = image_to_ds_icon(image_path)
    banner[32:544] = tile_bytes
    banner[544:576] = palette_bytes
    for i in range(6):
        set_ds_title(banner, i, title)
    return banner


rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])

# pull the SDAT out of the ROM
sound_id = rom.filenames.idOf('sound_data.sdat')
sdat = ndspy.soundArchive.SDAT(rom.files[sound_id])

# find the two SWARs we need
menu_swar = None
luigi_swar = None
for name, swar in sdat.waveArchives:
    if name == 'WAVE_VS_COMMON_MENU_SE':
        menu_swar = swar
    if name == 'WAVE_VS_COMMON_LUIGI_BASE_SE':
        luigi_swar = swar

# replace mario's sleep/wake voice lines with luigi's
# streams are zero-indexed here, vgmstream shows them as 1-indexed
menu_swar.waves[4] = luigi_swar.waves[2]  # it's-a-me...
menu_swar.waves[5] = luigi_swar.waves[4]  # ...mario!
menu_swar.waves[6] = luigi_swar.waves[1]  # ba-bye

rom.files[sound_id] = bytes(sdat.save())

# update icon and title in the ROM header
banner = bytearray(rom.iconBanner)
banner = update_icon_banner(banner, 'NSMB+.png', 'NSMB+\ncroaker.dev')
rom.iconBanner = bytes(banner)

rom.saveToFile(sys.argv[2])
print("saved to", sys.argv[2])
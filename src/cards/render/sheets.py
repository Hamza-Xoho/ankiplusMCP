"""Labelled v1 contact sheet layout, grouping the same notes on both sides."""
from PIL import Image, ImageChops, ImageDraw


def tile(items, path, tile_width=300, columns=4):
    tiles = []
    for label, png in items:
        with Image.open(png) as source:
            image = source.convert('RGB')
        background = Image.new('RGB', image.size, image.getpixel((2, max(0, image.height-2))))
        box = ImageChops.difference(image, background).getbbox()
        if box:
            image = image.crop((0, 0, image.width, min(image.height, box[3] + 16)))
        image = image.resize((tile_width, max(1, int(image.height * tile_width / image.width))))
        caption = Image.new('RGB', (tile_width, image.height + 22), (20, 22, 26))
        caption.paste(image, (0, 22))
        ImageDraw.Draw(caption).text((6, 5), label, fill=(240, 200, 90))
        tiles.append(caption)
    rows = [tiles[i:i+columns] for i in range(0, len(tiles), columns)]
    height = sum(max(t.height for t in row) + 8 for row in rows) + 8
    sheet = Image.new('RGB', (columns * (tile_width + 8) + 8, height), (10, 10, 12))
    y = 8
    for row in rows:
        x = 8
        for image in row:
            sheet.paste(image, (x, y))
            x += tile_width + 8
        y += max(image.height for image in row) + 8
    sheet.save(path)

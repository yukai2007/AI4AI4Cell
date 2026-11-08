"""Render review PDFs and numbered contact sheets for visual inspection."""
from pathlib import Path
import argparse

import fitz
from PIL import Image, ImageDraw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf', type=Path)
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    document = fitz.open(args.pdf)
    thumbs = []
    for index, page in enumerate(document):
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
        path = args.out / f'page-{index + 1:02d}.png'
        pix.save(path)
        thumb = Image.open(path).convert('RGB')
        thumb.thumbnail((420, 594))
        tile = Image.new('RGB', (440, 626), '#dddddd')
        tile.paste(thumb, ((440 - thumb.width) // 2, 22))
        ImageDraw.Draw(tile).text((12, 6), f'Page {index + 1}', fill='black')
        thumbs.append(tile)
    for start in range(0, len(thumbs), 6):
        sheet = Image.new('RGB', (1320, 1252), 'white')
        for offset, tile in enumerate(thumbs[start:start + 6]):
            sheet.paste(tile, ((offset % 3) * 440, (offset // 3) * 626))
        sheet.save(args.out / f'contact-{start // 6 + 1:02d}.png')
    print(f'Rendered {len(document)} pages to {args.out}')


if __name__ == '__main__':
    main()

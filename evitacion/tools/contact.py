"""Hoja de contactos de las vistas previas: python3 tools/contact.py salida.jpg a.png b.png ..."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

files = [Path(f) for f in sys.argv[2:]]
w, h, cols = 360, 640, min(6, len(sys.argv) - 2)
rows = (len(files) + cols - 1) // cols
sheet = Image.new("RGB", (cols * w + (cols - 1) * 8, rows * (h + 30)), "white")
d = ImageDraw.Draw(sheet)
for i, f in enumerate(files):
    x, y = (i % cols) * (w + 8), (i // cols) * (h + 30)
    sheet.paste(Image.open(f).convert("RGB").resize((w, h), Image.LANCZOS), (x, y + 30))
    d.text((x + 4, y + 8), f.stem, fill="black")
sheet.save(sys.argv[1], quality=88)

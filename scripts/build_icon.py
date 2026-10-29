"""Rebuild the original task-management mark and Windows icon with Pillow."""
from pathlib import Path
from PIL import Image, ImageDraw


def task_icon(size):
    # Draw at 4x resolution so check marks stay crisp in the taskbar/title bar.
    scale = 4
    canvas = Image.new('RGBA', (256 * scale, 256 * scale))
    mask = Image.new('L', canvas.size)
    ImageDraw.Draw(mask).rounded_rectangle((8*scale, 8*scale, 248*scale, 248*scale), radius=54*scale, fill=255)
    gradient = Image.new('RGBA', canvas.size)
    draw = ImageDraw.Draw(gradient)
    for y in range(256 * scale):
        t = y / (256 * scale - 1)
        color = tuple(round(a + (b-a)*t) for a, b in zip((151, 48, 76), (91, 24, 46))) + (255,)
        draw.line((0, y, 256*scale, y), fill=color)
    gradient.putalpha(mask)
    canvas.alpha_composite(gradient)
    draw = ImageDraw.Draw(canvas)
    def line(points, fill, width):
        points = [(round(x*scale), round(y*scale)) for x, y in points]
        draw.line(points, fill=fill, width=round(width*scale), joint='curve')
        r = width*scale/2
        for x, y in points:
            draw.ellipse((round(x-r), round(y-r), round(x+r), round(y+r)), fill=fill)
    # Two completed rows and a pending row: tasks, without letter initials.
    for y, length in ((76, 59), (128, 45)):
        line([(57,y), (69,y+12), (91,y-14)], '#fff5ed', 11)
        line([(119,y), (119+length,y)], '#fff5ed', 12)
    draw.rounded_rectangle((59*scale, 169*scale, 84*scale, 194*scale), radius=6*scale, outline='#e5b4c2', width=6*scale)
    line([(119,182), (187,182)], '#e5b4c2', 12)
    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def build():
    assets = Path(__file__).resolve().parents[1] / 'assets'
    icon = task_icon(256)
    icon.save(assets / 'icon.png')
    task_icon(24).save(assets / 'icon-24.png')
    # Supply individually rendered sizes instead of repeatedly scaling a tiny icon.
    icon.save(assets / 'icon.ico', sizes=[(s,s) for s in (16,24,32,48,64,128,256)],
              append_images=[task_icon(s) for s in (16,24,32,48,64,128)])


if __name__ == '__main__':
    build()

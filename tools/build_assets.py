"""Builds the icons, mark, favicon, page backdrop and link card in docs/img from Enderal LE's archives."""
import io, math
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps
import bsa

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'docs' / 'img'
FONTS = ROOT / 'research' / 'fonts'
ICON = 64
BRONZE = ((52, 36, 20), (236, 214, 170), (176, 141, 87))


def tex(path):
    b = bsa.extract('textures/' + path)
    if not b:
        raise FileNotFoundError(path)
    return Image.open(io.BytesIO(b)).convert('RGBA')


def centred(im, size=ICON, pad=2):
    im = im.crop(im.getchannel('A').getbbox())
    im.thumbnail((size - 2 * pad,) * 2, Image.LANCZOS)
    out = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    out.paste(im, ((size - im.width) // 2, (size - im.height) // 2), im)
    return out


def glow(im, colour, radius):
    """Soft halo of `colour` behind the opaque parts of `im`, so a dark glyph still reads on dark ground."""
    halo = Image.new('RGBA', im.size, colour)
    halo.putalpha(im.getchannel('A').filter(ImageFilter.GaussianBlur(radius)).point(lambda a: min(255, a * 2)))
    return Image.alpha_composite(halo, im)


# Spike lengths and angle offsets tracing the carved star in enderalsymbol.dds; its strokes are too thin to cut out.
SPIKES = [(1.0, 0), (.55, 4), (.92, -6), (.5, 3), (.78, 8), (.48, -4), (1.0, -3), (.52, 6), (.86, 2), (.46, -8), (.7, 5)]


def star(dark, light, mid, size=512):
    S = size
    c, R = S / 2, S * .47
    pts = []
    for k, (length, jitter) in enumerate(SPIKES):
        a = math.radians(-90 + k * 360 / len(SPIKES) + jitter)
        b = a + math.radians(180 / len(SPIKES))
        pts += [(c + R * length * math.cos(a), c + R * length * math.sin(a)), (c + R * .3 * math.cos(b), c + R * .3 * math.sin(b))]
    shape = Image.new('L', (S, S), 0)
    ImageDraw.Draw(shape).polygon(pts, fill=255)
    hole = Image.new('L', (S, S), 0)
    ImageDraw.Draw(hole).ellipse((c - R * .1, c - R * .1, c + R * .1, c + R * .1), fill=255)
    shape = ImageChops.subtract(shape, hole)
    shade = Image.radial_gradient('L').resize((S, S)).point(lambda v: 255 - v)
    im = ImageOps.colorize(shade, dark, light, mid)
    im.putalpha(shape)
    edge = shape.filter(ImageFilter.MaxFilter(9))
    outline = Image.new('RGBA', (S, S), dark + (255,))
    outline.putalpha(ImageChops.subtract(edge, shape))
    return Image.alpha_composite(outline, im)


def symbol_icon(dark, light, mid):
    return centred(glow(centred(star(dark, light, mid), 256, 20), mid + (170,), 8))


def ice_claw():
    cap = tex('enderal/plants/eispranke.dds').crop((0, 0, 256, 256))
    mask = Image.new('L', (256, 256), 0)
    ImageDraw.Draw(mask).ellipse((10, 10, 246, 246), fill=255)
    cap.putalpha(mask.filter(ImageFilter.GaussianBlur(2)))
    cap = ImageOps.autocontrast(cap.convert('RGB'), cutoff=1).convert('RGBA')
    cap.putalpha(mask.filter(ImageFilter.GaussianBlur(2)))
    rim = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
    ImageDraw.Draw(rim).ellipse((10, 10, 246, 246), outline=(18, 40, 52, 255), width=8)
    return centred(Image.alpha_composite(cap, rim))


def soul():
    wisp = tex('effects/magicsquiggles01.dds').crop((0, 0, 512, 512)).convert('L')
    wisp = ImageOps.autocontrast(wisp, cutoff=0.5)
    core = wisp.filter(ImageFilter.GaussianBlur(2))
    im = ImageOps.colorize(core, (20, 60, 52), (240, 255, 248), (120, 214, 180))
    im.putalpha(wisp.point(lambda v: min(255, int(v * 1.6))))
    orb = Image.new('RGBA', (512, 512), (190, 245, 220, 0))
    core_alpha = Image.new('L', (512, 512), 0)
    core_alpha.paste(Image.radial_gradient('L').resize((300, 300)).point(lambda v: max(0, 210 - v)), (106, 106))
    orb.putalpha(core_alpha.filter(ImageFilter.GaussianBlur(12)))
    return centred(glow(centred(Image.alpha_composite(orb, im), 256, 20), (120, 214, 180, 170), 9))


def horn():
    """A Vatyr horn drawn by hand: no fragment texture reads as anything at icon size."""
    S = 512
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pts_l, pts_r = [], []
    p0, p1, p2 = (120, 440), (60, 120), (400, 70)
    for k in range(41):
        t = k / 40
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
        dx = 2 * (1 - t) * (p1[0] - p0[0]) + 2 * t * (p2[0] - p1[0])
        dy = 2 * (1 - t) * (p1[1] - p0[1]) + 2 * t * (p2[1] - p1[1])
        n = math.hypot(dx, dy)
        w = 62 * (1 - t) ** 1.15 + 3
        pts_l.append((x - dy / n * w, y + dx / n * w))
        pts_r.append((x + dy / n * w, y - dx / n * w))
    outline = pts_l + pts_r[::-1]
    d.polygon(outline, fill=(214, 192, 150, 255))
    shade = Image.new('L', (S, S), 0)
    ImageDraw.Draw(shade).polygon(pts_r + [(S, 0), (S, S)], fill=150)
    body = Image.new('RGBA', (S, S), (96, 70, 40, 255))
    body.putalpha(ImageChops.multiply(shade.filter(ImageFilter.GaussianBlur(26)), im.getchannel('A')))
    im = Image.alpha_composite(im, body)
    d = ImageDraw.Draw(im)
    for k in range(4, 36, 4):
        a, b = pts_l[k], pts_r[k]
        d.line([a, b], fill=(120, 88, 52, 255), width=7)
    d.line(outline + [outline[0]], fill=(40, 26, 14, 255), width=12, joint='curve')
    return centred(glow(im, (184, 146, 90, 120), 10))


def mark():
    return centred(star(*BRONZE, size=800), 200, 4)


def backdrop():
    """Ark at night, one of the game's loading screens, unsquashed to 16:9 and sunk into the page's black."""
    art = tex('enderal/forgottenstories/loadscreens/loadscreenarknight.dds').convert('RGB').resize((1920, 1080), Image.LANCZOS)
    art = art.filter(ImageFilter.GaussianBlur(1.2))
    art = Image.blend(art, Image.new('RGB', art.size, (13, 11, 10)), 0.45)
    return art


def og_card(icons):
    W, H = 1200, 630
    wall = tex('interface/objects/mainmenuwallpaper.dds').convert('RGB')
    wall = wall.crop(wall.convert('L').point(lambda v: 255 if v > 12 else 0).getbbox())
    card = ImageOps.fit(wall, (W, H), Image.LANCZOS, centering=(0.5, 0.45))
    card = Image.blend(card, Image.new('RGB', (W, H), (13, 11, 10)), 0.62)
    vig = Image.new('L', (W, H), 0)
    ImageDraw.Draw(vig).ellipse((-W * .2, -H * .5, W * 1.2, H * 1.5), fill=255)
    card = Image.composite(card, Image.new('RGB', (W, H), (8, 6, 5)), vig.filter(ImageFilter.GaussianBlur(110)))
    d = ImageDraw.Draw(card)
    title = ImageFont.truetype(str(FONTS / 'Cinzel.ttf'), 68)
    title.set_variation_by_axes([600])
    sub = ImageFont.truetype(str(FONTS / 'EBGaramond.ttf'), 34)

    def line(text, font, y, fill, spacing=0):
        x = W / 2
        for dy, colour in ((3, (0, 0, 0)), (0, fill)):
            d.text((x, y + dy), text, font=font, fill=colour, anchor='mm')

    m = mark().resize((112, 112), Image.LANCZOS)
    card.paste(m, (int(W / 2 - 56), 58), m)
    line('ENDERAL COLLECTIBLES', title, 236, (232, 214, 176))
    d.line([(W / 2 - 250, 286), (W / 2 + 250, 286)], fill=(176, 141, 87), width=2)
    line('Drop in a save — LE or SE — and see what you still have to find', sub, 330, (205, 186, 152))
    gap = 54
    x = int((W - (len(icons) * 88 + (len(icons) - 1) * gap)) / 2)
    for ic in icons:
        ic = ic.resize((88, 88), Image.LANCZOS)
        card.paste(ic, (x, 420), ic)
        x += 88 + gap
    return card


OUT.mkdir(parents=True, exist_ok=True)
icons = {
    'symbol': symbol_icon((70, 20, 4), (255, 214, 120), (226, 110, 30)),
    'mystic': symbol_icon((34, 10, 60), (236, 210, 255), (150, 84, 230)),
    'soul': soul(),
    'fragment': horn(),
    'iceclaw': ice_claw(),
}
for k, im in icons.items():
    im.save(OUT / f'{k}.png', optimize=True)

mk = mark()
mk.save(OUT / 'mark.png', optimize=True)
ico = Image.new('RGBA', (512, 512), (13, 11, 10, 255))
g = mk.resize((440, 440), Image.LANCZOS)
ico.paste(g, (36, 36), g)
ico.convert('RGB').save(ROOT / 'docs' / 'favicon.ico', sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
ico.resize((180, 180), Image.LANCZOS).save(OUT / 'icon-180.png', optimize=True)

backdrop().save(OUT / 'backdrop.jpg', quality=78, optimize=True, progressive=True)
og_card(list(icons.values())).save(OUT / 'og.jpg', quality=88, optimize=True, progressive=True)

for f in sorted(OUT.iterdir()):
    print(f.name, f.stat().st_size)

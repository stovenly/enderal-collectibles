"""Builds the icons, mark, favicon, page backdrop and link card in docs/img from Enderal LE's archives."""
import io
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps
import bsa, render

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'docs' / 'img'
FONTS = ROOT / 'research' / 'fonts'
ICON = 64


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


SYMBOL_MESH = 'meshes/enderal/miscellaneous/enderalsymbolanimatedfx.nif'
MYSTIC_MESH = 'meshes/enderal/forgottenstories/clutter/enderalsymbolanimatedfx.nif'
ICE_CLAW_MESH = 'meshes/enderal/landscape/bluemushroom.nif'
HORN_MESH = 'meshes/enderal/forgottenstories/miscellaneous/lefthorn.nif'


def emblem(mesh, glow_strength, ambient=.45):
    """The Enderal emblem a symbol is modelled as, crescent up and tail down like SureAI's logo."""
    return render.render(mesh, 768, emissive=glow_strength, ambient=ambient).rotate(90)


def symbol_icon(mesh):
    return centred(emblem(mesh, .7))


def brighten(im, k):
    alpha = im.getchannel('A')
    im = ImageEnhance.Brightness(im.convert('RGB')).enhance(k).convert('RGBA')
    im.putalpha(alpha)
    return im


def ice_claw():
    return centred(render.render(ICE_CLAW_MESH, 512, view=(1, -1, -.5), emissive=.3))


def fragment():
    return centred(glow(centred(brighten(render.render(HORN_MESH, 512, ambient=.8), 2.1), 256, 12), (184, 146, 90, 90), 5))


def soul():
    """A ghost: the soul effect is a particle swirl that reads as nothing at icon size."""
    S = 512
    shape = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(shape)
    d.ellipse((126, 60, 386, 320), fill=255)
    d.rectangle((126, 190, 386, 400), fill=255)
    for k in range(4):
        x = 126 + k * 65
        d.ellipse((x, 368, x + 65, 440), fill=255 if k % 2 == 0 else 0)
    for k in (1, 3):
        x = 126 + k * 65
        d.ellipse((x, 348, x + 65, 420), fill=0)
    eyes = Image.new('L', (S, S), 0)
    e = ImageDraw.Draw(eyes)
    e.ellipse((190, 170, 236, 236), fill=255)
    e.ellipse((276, 170, 322, 236), fill=255)
    shape = ImageChops.subtract(shape.filter(ImageFilter.GaussianBlur(2)), eyes)
    body = ImageOps.colorize(Image.linear_gradient('L').resize((S, S)), (226, 255, 244), (70, 170, 140), (150, 225, 196))
    body.putalpha(shape.point(lambda a: int(a * .92)))
    return centred(glow(centred(body, 256, 18), (110, 214, 176, 190), 9))


def mark():
    return centred(brighten(emblem(SYMBOL_MESH, 0, ambient=.9), 2.4), 200, 4)


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
    'symbol': symbol_icon(SYMBOL_MESH),
    'mystic': symbol_icon(MYSTIC_MESH),
    'soul': soul(),
    'fragment': fragment(),
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

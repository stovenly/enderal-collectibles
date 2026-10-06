"""Builds a tracker page per collectible, and the sitemap, by retargeting docs/index.html."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / 'docs'
SITE = 'https://stovenly.github.io/enderal-collectibles/'

PAGES = {
    'symbol': dict(
        slug='magic-symbols', name='Magic Symbols', total=100,
        lead='Find the Magic Symbols you are missing',
        what='<p>There are 100 Magic Symbols carved into ruins, caves and cliffsides across Vyn, each one glowing '
             'faintly in the stone. Touching one grants experience, more for every symbol you have already found, '
             'and collecting all of them unlocks an achievement.</p>',
        why='<p>The game tells you how many you have, but never which. Past the first fifty or so the count stops '
            'being much help: the rest are tucked into the backs of dungeons you have already cleared, or out in '
            'country you only crossed once.</p>',
        extra='<p>It also reads the game&rsquo;s own symbol counter and tells you if it disagrees with the save, '
              'which usually means a mod or a console command has touched one.</p>'),
    'mystic': dict(
        slug='mystical-symbols', name='Mystical Symbols', total=15,
        lead='Find the Mystical Symbols you are missing',
        what='<p>Forgotten Stories adds 15 Mystical Symbols, the violet counterpart to the Magic Symbols. Most sit '
             'in places you only pass through during its quests: a castle, a crypt, a theatre in the Undercity, '
             'another reality altogether.</p>',
        why='<p>Because so many are tied to a quest, it is worth knowing which ones you still owe yourself before '
            'you finish the questline that leads to them.</p>',
        extra=''),
    'soul': dict(
        slug='phasmalist-souls', name='Phasmalist Souls', total=20,
        lead='Find the Phasmalist Souls you are missing',
        what='<p>Twenty souls of the dead wait around Vyn for a Phasmalist to bind them into talismans. They only '
             'appear once the Net of Souls talent is strong enough for their rank, so most players walk straight '
             'past a few of them the first time.</p>',
        why='<p>Gather all twenty and the quest Souls rewards you with a hidden sixth-rank soul. A couple of '
            'them are only reachable during a quest, which makes it easy to lose one for good.</p>',
        extra='<p>A soul counts as collected once it is in your inventory, even if you have since bound it into a '
              'talisman.</p>'),
    'fragment': dict(
        slug='vatyra-fragments', name='Vatyra Fragments', total=9,
        lead='Find the Vatyra Fragments you are missing',
        what='<p>The Forgotten Stories quest Home of the Forsaken asks you to gather nine fragments &mdash; horns, '
             'ears, eyes, teeth and a ring &mdash; and set them back in their places to open a hidden door. They '
             'are scattered from a trading post in Ark to the Powder Desert.</p>',
        why='<p>Nothing in the journal says which pieces you still lack, only how many you have, and the fragments '
            'look alike once they are in your pack.</p>',
        extra=''),
    'iceclaw': dict(
        slug='ice-claws', name='Ice Claws', total=230,
        lead='Find the Ice Claws you are missing',
        what='<p>Ice Claws are pale blue mushrooms, and eating one raises your carrying capacity by 1 for good. '
             'There are 230 in all: 229 growing across Vyn and its dungeons, and one in the pocket of Ark&rsquo;s '
             'harbormaster.</p>',
        why='<p>With that many spread over the whole map, keeping track by hand is hopeless, and most guides are '
            'short of the real total.</p>',
        extra='<p>The game counts the claws you pick, but not the one you take from Harbormaster Rewald; the '
              'tracker checks his inventory for that.</p>'),
}


def about(spec):
    extra = spec['extra'] + '\n' if spec['extra'] else ''
    return f'''  <section id="about" class="about panel">
    <h2>{spec['lead']}</h2>
{spec['what']}
{spec['why']}

    <h2>What this page does</h2>
    <p>Drop your save in above, from either Enderal (Classic) or Enderal Special Edition, and it works out which of
      the {spec['total']} {spec['name']} you have already taken. Whatever is left is listed with the location of each
      one and pinned on the world map.</p>
    <p>The save is read in your browser. Nothing is uploaded, and there is nothing to install.</p>
{extra}    <p>If you would rather see everything at once, the <a href="../">full tracker</a> covers all five kinds
      of collectible together.</p>
  </section>
'''


def retarget(src, kind, spec):
    n, name, slug = spec['total'], spec['name'], spec['slug']
    title = f'Enderal {name} Tracker — see which of the {n} you are missing'
    desc = (f'Drop an Enderal or Enderal Special Edition save on the page and see which of the {n} {name} you have '
            f'not collected yet, listed with their locations and pinned on the world map.')
    s = src
    s = re.sub(r'<title>.*?</title>', f'<title>{title}</title>', s, count=1)
    s = re.sub(r'<meta name="description" content=".*?">', f'<meta name="description" content="{desc}">', s, count=1)
    s = s.replace(f'<link rel="canonical" href="{SITE}">', f'<link rel="canonical" href="{SITE}{slug}/">')
    s = s.replace('<meta property="og:title" content="Enderal Collectibles Tracker">', f'<meta property="og:title" content="{title}">')
    s = s.replace('<meta name="twitter:title" content="Enderal Collectibles Tracker">', f'<meta name="twitter:title" content="{title}">')
    s = re.sub(r'<meta property="og:description" content=".*?">', f'<meta property="og:description" content="{desc}">', s, count=1)
    s = re.sub(r'<meta name="twitter:description" content=".*?">', f'<meta name="twitter:description" content="{desc}">', s, count=1)
    s = s.replace(f'<meta property="og:url" content="{SITE}">', f'<meta property="og:url" content="{SITE}{slug}/">')
    s = re.sub(r'<script type="application/ld\+json">.*?</script>', f'''<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "WebApplication",
  "name": "Enderal {name} Tracker",
  "url": "{SITE}{slug}/",
  "applicationCategory": "GameApplication",
  "operatingSystem": "Any browser",
  "browserRequirements": "Requires JavaScript",
  "offers": {{ "@type": "Offer", "price": "0", "priceCurrency": "USD" }},
  "description": "{desc}",
  "screenshot": "{SITE}img/og.jpg",
  "about": {{ "@type": "VideoGame", "name": "Enderal: Forgotten Stories", "publisher": {{ "@type": "Organization", "name": "SureAI" }} }}
}}
</script>''', s, count=1, flags=re.S)

    for attr in ('href', 'src'):
        for d in ('img/', 'css/', 'js/', 'data/'):
            s = s.replace(f'{attr}="{d}', f'{attr}="../{d}')
    s = s.replace('href="favicon.ico"', 'href="../favicon.ico"')
    for page in PAGES.values():
        s = s.replace(f'href="{page["slug"]}/"', f'href="../{page["slug"]}/"')

    s = s.replace('<body>', f'<body data-kind="{kind}">', 1)
    s = s.replace('<h1>Enderal Collectibles Tracker</h1>', f'<h1>Enderal {name}</h1>', 1)
    s = s.replace('<main class="wrap">',
                  '<main class="wrap">\n  <nav class="crumbs"><a href="../">Enderal Collectibles Tracker</a> '
                  f'&rsaquo; {name}</nav>\n', 1)

    start = s.index('  <section id="about"')
    end = s.index('</section>', start) + len('</section>\n')
    return s[:start] + about(spec) + s[end:]


src = (DOCS / 'index.html').read_text(encoding='utf-8')
for kind, spec in PAGES.items():
    d = DOCS / spec['slug']
    d.mkdir(parents=True, exist_ok=True)
    (d / 'index.html').write_text(retarget(src, kind, spec), encoding='utf-8')
    print(spec['slug'], spec['total'], spec['name'])

urls = [SITE] + [SITE + s['slug'] + '/' for s in PAGES.values()]
(DOCS / 'sitemap.xml').write_text(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + ''.join(f'  <url>\n    <loc>{u}</loc>\n    <changefreq>monthly</changefreq>\n'
              f'    <priority>{"1.0" if u == SITE else "0.8"}</priority>\n  </url>\n' for u in urls)
    + '</urlset>\n', encoding='utf-8')
(DOCS / 'robots.txt').write_text(f'User-agent: *\nAllow: /\n\nSitemap: {SITE}sitemap.xml\n', encoding='utf-8')
print('sitemap', len(urls), 'urls')

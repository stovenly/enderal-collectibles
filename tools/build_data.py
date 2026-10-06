"""Builds docs/data/collectibles.json from Enderal LE's plugins, the SureAI Wiki notes and tools/item_notes.json."""
import json, math, re, struct
from collections import Counter, deque
from pathlib import Path
import tes5
from kinds import SCRIPTS, ICE_CLAW_ITEM

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'docs' / 'data'
WIKI = ROOT / 'research' / 'wiki'

PREFIX = {'symbol': ('MS', 3), 'mystic': ('MY', 2), 'soul': ('PS', 2), 'fragment': ('VF', 1), 'iceclaw': ('IC', 3)}
COUNTERS = {
    'symbol': '_00E_MagicalSymbolsGlobalCollected',
    'mystic': '_00E_FS_MysticalSymbolsGlobalCollected',
    'soul': 'FS_NQ09_SoulsCollected',
    'fragment': '_00E_FS_NQ10_MiscCountGlobal',
    'iceclaw': '_00E_EisprankeCounter',
}
# The Ice Claw counter only counts plants, so a carried claw is checked against the holder's inventory instead.
NOT_HOLDERS = {'_00E_Test_Container_PotionsAndPoison'}
FRAGMENT_ORDER = ['Ring', 'LeftEar', 'RightEar', 'LeftEye', 'RightEye', 'LeftHorn', 'RightHorn', 'LeftTooth', 'RightTooth']
SOUL_CLASSES = ['Archer', 'Hybrid', 'Wildmage', 'Warrior']
MAP_MARKER = 0x10
UNITS_PER_M = 70.0
LAND_DATA = 0x1

# SureAI's map, https://map.enderal.sureai.net/Config.js: offsets in cells, applied before the scale.
PROJ = dict(sx=91.80, ox=52.95, sy=94.25, oy=41.25)
TILES = dict(path='map/vyn', size=256, min=2, max=5)

# One-time areas with no place on the painted map get a fixed spot in the sea east of the continent.
REALM_PINS = {
    'halfmoon': dict(name='Halfmoon Isle', u=0.935, v=0.585),
    'starcity': dict(name='Starcity', u=0.935, v=0.665),
}
REALMS = {
    'MQ09Isle': dict(pin='halfmoon', note="Halfmoon Isle, off the east coast. Only reachable during the main quest The Lion's Den."),
    'StarCityNewHarbour': dict(pin='starcity', note='Only reachable during the main quest Forgotten Homeland, Part II.'),
    'MQ13cBotanicum': dict(pin='starcity', note='Only reachable during the main quest Forgotten Homeland, Part III.'),
    'FS_NQ01_Qyra_Island': dict(area='Another reality', note="Only reachable during the Forgotten Stories quest A Drop in an Ocean, through the Planeswalker in Zorkban's Cellar."),
}
# Interiors entered through scripted walls or quest teleports, which door-walking cannot follow.
MARKER_PINS = {'FlusshaimHousePhasmalism': 'Riverville', 'FS_NQ03_Theater': 'Entrance to the Undercity'}

recs = tes5.load('le')
by_edid = {}
for r in recs.values():
    if r.type not in ('REFR', 'ACHR', 'NAVM', 'LAND') and r.edid:
        by_edid.setdefault(r.edid, r)
VYN = by_edid['Vyn'].fid


def u32(b):
    return struct.unpack_from('<I', b)[0]


def plugin_key(fid):
    return {tes5.SKYRIM: 'skyrim', tes5.FS: 'fs'}[fid >> 24]


shared = {VYN}
for r in recs.values():
    if r.type == 'WRLD' and r.ref('WNAM') == VYN and r.sub('PNAM') and r.sub('PNAM')[0] & LAND_DATA:
        shared.add(r.fid)

base_kind = {}
for r in recs.values():
    if r.type in ('ACTI', 'MISC') and r.sub('VMAD'):
        hit = [SCRIPTS[s.lower()] for s in tes5.vmad_scripts(r.sub('VMAD')) if s.lower() in SCRIPTS]
        if hit:
            base_kind[r.fid] = hit[0]

refs, doors, cells_by_world, markers, placed_by_base = {}, {}, {}, [], {}
for r in recs.values():
    if r.type not in ('REFR', 'ACHR') or not r.sub('DATA'):
        continue
    cell, wrld = r.cell_world()
    pos = struct.unpack('<3f', r.sub('DATA')[:12])
    refs[r.fid] = (cell, wrld, pos)
    base = r.ref('NAME')
    placed_by_base.setdefault(base, []).append(r.fid)
    if wrld is not None:
        cells_by_world.setdefault(wrld, set()).add(cell)
    if r.sub('XTEL'):
        doors.setdefault(cell, []).append(r.ref('XTEL'))
    if base == MAP_MARKER and wrld in shared and r.full:
        markers.append(dict(name=r.full, x=pos[0], y=pos[1]))

DIRS = ['E', 'NE', 'N', 'NW', 'W', 'SW', 'S', 'SE']


def nearest_marker(x, y):
    m = min(markers, key=lambda m: math.hypot(x - m['x'], y - m['y']))
    d = math.hypot(x - m['x'], y - m['y'])
    ang = math.degrees(math.atan2(y - m['y'], x - m['x'])) % 360
    return dict(name=m['name'], metres=round(d / UNITS_PER_M), dir=DIRS[int((ang + 22.5) // 45) % 8])


def marker(name):
    m = next((m for m in markers if m['name'] == name), None)
    assert m, f'no map marker named {name!r}'
    return m['x'], m['y']


def exit_to_vyn(seeds, home):
    """BFS through load doors until one opens into Vyn or a worldspace sharing its grid."""
    seen, q = set(seeds), deque(seeds)
    while q:
        c = q.popleft()
        for dest in doors.get(c, []):
            if dest not in refs:
                continue
            dcell, dwrld, dpos = refs[dest]
            if dwrld in shared and dwrld != home:
                return dpos
            nxt = cells_by_world.get(dwrld, ()) if dwrld is not None and dwrld != home else (dcell,)
            for n in nxt:
                if n not in seen:
                    seen.add(n)
                    q.append(n)


def map_uv(x, y):
    return (round((x / 4096 + PROJ['ox']) / PROJ['sx'], 5),
            round(1 - (y / 4096 + PROJ['oy']) / PROJ['sy'], 5))


def locate(item, cell, wrld, pos):
    c = recs[cell]
    w = recs[wrld] if wrld is not None else None
    item['interior'] = wrld is None
    if wrld is None:
        item['area'] = c.full or c.edid
        item['cell'] = c.edid
    elif wrld not in shared:
        item['area'] = w.full or w.edid
    realm = REALMS.get(c.edid) or (REALMS.get(w.edid) if w else None)
    if realm:
        item['realm'] = True
        item['realmNote'] = realm['note']
        item['area'] = realm.get('area', item.get('area'))
    if realm and realm.get('pin'):
        p = REALM_PINS[realm['pin']]
        item['map'] = dict(u=p['u'], v=p['v'], realm=p['name'])
        return
    if wrld in shared:
        opos, via = pos, False
    elif c.edid in MARKER_PINS:
        opos, via = marker(MARKER_PINS[c.edid]), True
    else:
        opos, via = exit_to_vyn(list(cells_by_world[wrld]) if wrld is not None else [cell], wrld), True
    assert opos, f'no way out to Vyn from {c.edid or w.edid}'
    u, v = map_uv(opos[0], opos[1])
    item['map'] = dict(u=u, v=v)
    item['near'] = nearest_marker(opos[0], opos[1])
    item['viaDoor'] = via


def wiki_clean(s):
    s = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]', r'\1', s)
    s = re.sub(r"'''?|<br\s*/?>", '', s)
    s = re.sub(r'\[@[^\]]*\]', '', s)
    return re.sub(r'\s+', ' ', s).strip(' ,')


def soul_notes():
    """Location column of the Phasmalism page's soul table, keyed by the soul's FS-local form ID."""
    text = (WIKI / 'Phasmalism.txt').read_text(encoding='utf-8')
    table = text[text.index('===Soul List==='):]
    table = table[:table.index('\n|}')]
    out = {}
    for row in table.split('\n|-')[1:]:
        m = re.search(r'\{\{FormID\|xx\|([0-9A-Fa-f]{6})\}\}', row)
        if not m:
            continue
        cells = re.split(r'\n\|', row)
        loc = next((wiki_clean(c) for c in reversed(cells) if c.strip() and '[[File:' not in c), '')
        out[int(m.group(1), 16)] = loc
    return out


def symbol_rows():
    rows, region = [], None
    for line in (WIKI / 'Magical_Symbol.txt').read_text(encoding='utf-8').split('\n'):
        m = re.match(r"^'''(.+?):?'''", line.strip())
        if m:
            region = m.group(1).rstrip(':')
        elif line.startswith('*') and region:
            rows.append(dict(region=region, text=wiki_clean(line.lstrip('* '))))
    return rows


items = []
for fid, (cell, wrld, pos) in refs.items():
    r = recs[fid]
    if r.type != 'REFR' or r.ref('NAME') not in base_kind:
        continue
    base = recs[r.ref('NAME')]
    kind = base_kind[base.fid]
    item = dict(id='', kind=kind, plugin=plugin_key(fid), ref=fid & 0xFFFFFF)
    if kind in ('soul', 'fragment'):
        item['name'] = base.full
        item['_base'] = base
    locate(item, cell, wrld, pos)
    item['_sort'] = fid
    items.append(item)

claw = by_edid[ICE_CLAW_ITEM]
for npc in recs.values():
    if npc.type != 'NPC_' or npc.edid in NOT_HOLDERS:
        continue
    for v in npc.all('CNTO'):
        if npc.plugin.norm(u32(v)) != claw.fid:
            continue
        holder = placed_by_base[npc.fid][0]
        for nth in range(1, struct.unpack_from('<i', v, 4)[0] + 1):
            item = dict(id='IC-R', kind='iceclaw', plugin=plugin_key(holder), ref=0, holder=holder & 0xFFFFFF,
                        holderPlugin=plugin_key(holder), item=claw.fid & 0xFFFFFF, itemPlugin=plugin_key(claw.fid), nth=nth,
                        note=f'Carried by {npc.full}. Pickpocket it, or take it from his body.')
            locate(item, *refs[holder])
            item['area'] = f"{npc.full}, {item['area']}"
            item['_sort'] = 1 << 40
            items.append(item)

souls = soul_notes()


def soul_key(i):
    m = re.search(r'Phasmalist_Soul_(\w+)_Tier(\d)', i['_base'].edid)
    return int(m.group(2)), SOUL_CLASSES.index(m.group(1))


def fragment_key(i):
    return FRAGMENT_ORDER.index(re.search(r'NQ10_(\w+)Misc', i['_base'].edid).group(1))


for kind, (prefix, width) in PREFIX.items():
    group = [i for i in items if i['kind'] == kind and not i['id']]
    key = {'soul': soul_key, 'fragment': fragment_key}.get(kind, lambda i: i['_sort'])
    for n, it in enumerate(sorted(group, key=key), 1):
        it['id'] = f'{prefix}{n:0{width}d}'
    if kind == 'soul':
        for it in group:
            note = souls.get(it['_base'].fid & 0xFFFFFF)
            if note:
                it['note'] = note

symbol_map = json.loads((ROOT / 'tools' / 'symbol_wiki_map.json').read_text(encoding='utf-8'))
rows = symbol_rows()
def symbol_note(text, item):
    """The wiki line without its (interior)/(exterior, …) wrappers, or nothing if all it says is the place's name."""
    t = re.sub(r'^\((?:(?:exterior|interior),?\s*)?(.*)\)$', r'\1', text.strip())
    t = re.sub(r'\s*\((?:interior|exterior)\)', '', t)
    t = re.sub(r',?\s*coordinates:.*$', '', t).replace('Homelamd', 'Homeland').strip(' ,.')
    place = (item.get('area') or (item.get('near') or {}).get('name') or '').lower()
    if len(t.split()) < 3 or t.lower() in place:
        return None
    return t[0].upper() + t[1:] + ('' if t.endswith(('.', '!')) else '.')


for it in items:
    if it['id'] in symbol_map:
        row = rows[symbol_map[it['id']]]
        note = symbol_note(row['text'], it)
        if note:
            it['note'] = note
        it['region'] = row['region']

item_notes = json.loads((ROOT / 'tools' / 'item_notes.json').read_text(encoding='utf-8'))
for it in items:
    if it['id'] in item_notes:
        it['note'] = item_notes[it['id']]
    for k in ('_base', '_sort'):
        it.pop(k, None)

items.sort(key=lambda i: i['id'])
assert len({i['id'] for i in items}) == len(items)
counters = {k: dict(plugin=plugin_key(by_edid[e].fid), id=by_edid[e].fid & 0xFFFFFF) for k, e in COUNTERS.items()}

OUT.mkdir(parents=True, exist_ok=True)
world = dict(name=recs[VYN].full, image='data/vyn.webp', width=2048, height=2048, tiles=TILES)
(OUT / 'collectibles.json').write_text(json.dumps(
    dict(worlds=dict(vyn=world), counters=counters, realms=list(REALM_PINS.values()), items=items),
    ensure_ascii=False, separators=(',', ':')), encoding='utf-8')

print(Counter(i['kind'] for i in items))
print('realm:', [(i['id'], i['area']) for i in items if i.get('realm')])
print('via marker pins:', [(i['id'], i['area']) for i in items if i.get('cell') in MARKER_PINS])
print('souls without a wiki note:', [i['id'] for i in items if i['kind'] == 'soul' and not i.get('note')])
print('symbols with a wiki note:', sum(1 for i in items if i['kind'] == 'symbol' and i.get('note')), 'of', len(rows), 'wiki rows')

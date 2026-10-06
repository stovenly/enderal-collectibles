"""Fails unless Enderal LE and SE place every collectible identically, so one collectibles.json serves both."""
import struct, sys
import tes5
from kinds import SCRIPTS, ICE_CLAW_ITEM


def placements(edition):
    recs = tes5.load(edition)
    bases = {r.fid for r in recs.values() if r.type in ('ACTI', 'MISC') and r.sub('VMAD')
             and any(s.lower() in SCRIPTS for s in tes5.vmad_scripts(r.sub('VMAD')))}
    bases |= {r.fid for r in recs.values() if r.edid == ICE_CLAW_ITEM}
    out = {}
    for r in recs.values():
        if r.type in ('REFR', 'ACHR') and r.ref('NAME') in bases:
            cell, wrld = r.cell_world()
            out[r.fid] = dict(base=r.ref('NAME'), wrld=wrld, cell=cell, flags=r.flags & 0x820,
                              data=struct.unpack('<6f', r.sub('DATA')), parent=r.ref('XESP'))
    return out


le, se = placements('le'), placements('se')
problems = [f'{fid:08X} only in {"LE" if fid in le else "SE"}' for fid in le.keys() ^ se.keys()]
for fid in le.keys() & se.keys():
    a, b = le[fid], se[fid]
    for k in ('base', 'wrld', 'cell', 'flags', 'parent'):
        if a[k] != b[k]:
            problems.append(f'{fid:08X} {k}: LE {a[k]} SE {b[k]}')
    if max(abs(x - y) for x, y in zip(a['data'], b['data'])) > 1:
        problems.append(f'{fid:08X} moved: LE {a["data"]} SE {b["data"]}')
print(f'{len(le)} placements in LE, {len(se)} in SE')
print('\n'.join(problems) or 'identical')
sys.exit(1 if problems else 0)

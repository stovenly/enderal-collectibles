"""Skyrim-engine plugin reader for Enderal LE and SE: merged records, localized strings, VMAD script names."""
import os, struct, zlib

STEAM = r'C:\Program Files (x86)\Steam\steamapps\common'
DATA = {'le': os.path.join(STEAM, 'Enderal', 'Data'), 'se': os.path.join(STEAM, 'Enderal Special Edition', 'Data')}
# Normalised form IDs carry the index into this list, so both editions agree: SE's FS lists Update.esm as a master, LE's does not.
ORDER = ['Skyrim.esm', 'Update.esm', 'Enderal - Forgotten Stories.esm']
SKYRIM, FS = 0, 2
LOCALIZED = 0x80
COMPRESSED = 0x40000
FID_GROUPS = {1, 6, 8, 9, 10}


def u32(b):
    return struct.unpack_from('<I', b)[0]


def subrecords(buf):
    i, big = 0, None
    while i + 6 <= len(buf):
        t = buf[i:i + 4].decode('latin1')
        sz = struct.unpack_from('<H', buf, i + 4)[0]
        i += 6
        if t == 'XXXX':
            big = struct.unpack_from('<I', buf, i)[0]
            i += sz
            continue
        if big is not None:
            sz, big = big, None
        yield t, buf[i:i + sz]
        i += sz


class Plugin:
    def __init__(self, data_dir, name):
        self.name = name
        with open(os.path.join(data_dir, name), 'rb') as f:
            self.buf = f.read()
        hsize = struct.unpack_from('<I', self.buf, 4)[0]
        self.flags = struct.unpack_from('<I', self.buf, 8)[0]
        masters = [v.split(b'\0')[0].decode('latin1') for k, v in subrecords(self.buf[24:24 + hsize]) if k == 'MAST']
        index = {n.lower(): i for i, n in enumerate(ORDER)}
        self.remap = {i: index.get(m.lower(), 0xFF) for i, m in enumerate(masters)}
        self.remap[len(masters)] = index[name.lower()]
        self.strings = load_strings(data_dir, name) if self.flags & LOCALIZED else {}

    def norm(self, fid):
        return (self.remap.get(fid >> 24, 0xFF) << 24) | (fid & 0xFFFFFF)

    def text(self, b):
        if not b:
            return ''
        if self.flags & LOCALIZED and len(b) == 4:
            return self.strings.get(u32(b), '')
        return b.split(b'\0')[0].decode('cp1252', errors='replace')


class Rec:
    __slots__ = ('type', 'flags', 'fid', 'raw', 'path', 'plugin', '_d')

    @property
    def data(self):
        if self._d is None:
            self._d = zlib.decompress(self.raw[4:]) if self.flags & COMPRESSED else self.raw
        return self._d

    def subs(self):
        return list(subrecords(self.data))

    def sub(self, t):
        for k, v in subrecords(self.data):
            if k == t:
                return v

    def all(self, t):
        return [v for k, v in subrecords(self.data) if k == t]

    def ref(self, t, offset=0):
        v = self.sub(t)
        return self.plugin.norm(u32(v[offset:])) if v and len(v) >= offset + 4 else None

    @property
    def edid(self):
        v = self.sub('EDID')
        return v.split(b'\0')[0].decode('cp1252') if v else ''

    @property
    def full(self):
        return self.plugin.text(self.sub('FULL'))

    def cell_world(self):
        cell = wrld = None
        for gtype, label in self.path:
            if gtype == 1:
                wrld = label
            elif gtype in (6, 8, 9, 10):
                cell = label
        return cell, wrld


def walk(p, start, end, path=()):
    buf, i = p.buf, start
    while i < end:
        if buf[i:i + 4] == b'GRUP':
            gsz, label, gtype = struct.unpack_from('<I4si', buf, i + 4)
            lab = p.norm(u32(label)) if gtype in FID_GROUPS else label
            yield from walk(p, i + 24, i + gsz, path + ((gtype, lab),))
            i += gsz
        else:
            dsz, flags, fid = struct.unpack_from('<III', buf, i + 4)
            r = Rec()
            r.type, r.flags, r.fid = buf[i:i + 4].decode('latin1'), flags, p.norm(fid)
            r.raw, r.path, r.plugin, r._d = buf[i + 24:i + 24 + dsz], path, p, None
            yield r
            i += 24 + dsz


def load(edition):
    """Every record of the three plugins, later plugins overriding earlier ones by form ID."""
    recs = {}
    for name in ORDER:
        p = Plugin(DATA[edition], name)
        for r in walk(p, 24 + struct.unpack_from('<I', p.buf, 4)[0], len(p.buf)):
            recs[r.fid] = r
    return recs


def load_strings(data_dir, plugin):
    base = os.path.splitext(plugin)[0].lower() + '_english.'
    sdir = os.path.join(data_dir, 'Strings')
    out = {}
    if not os.path.isdir(sdir):
        return out
    for fn in os.listdir(sdir):
        if not fn.lower().startswith(base):
            continue
        sized = not fn.lower().endswith('.strings')
        b = open(os.path.join(sdir, fn), 'rb').read()
        n = struct.unpack_from('<I', b)[0]
        dbase = 8 + n * 8
        for k in range(n):
            sid, off = struct.unpack_from('<II', b, 8 + k * 8)
            o = dbase + off
            s = b[o + 4:o + 4 + u32(b[o:])] if sized else b[o:b.index(b'\0', o)]
            out[sid] = s.split(b'\0')[0].decode('cp1252', errors='replace')
    return out


def vmad_scripts(v):
    """Script names attached by a VMAD subrecord; properties are skipped."""
    if not v:
        return []
    ver, objfmt, n = struct.unpack_from('<hhH', v)
    names, o = [], 6
    for _ in range(n):
        ln = struct.unpack_from('<H', v, o)[0]
        names.append(v[o + 2:o + 2 + ln].decode('latin1'))
        o += 2 + ln + (1 if ver >= 4 else 0)
        count = struct.unpack_from('<H', v, o)[0]
        o += 2
        for _ in range(count):
            o += 2 + struct.unpack_from('<H', v, o)[0]
            t = v[o]
            o += 2 if ver >= 4 else 1
            o = _skip_property(v, o, t)
    return names


def _skip_property(v, o, t):
    if t == 1:
        return o + 8
    if t == 2:
        return o + 2 + struct.unpack_from('<H', v, o)[0]
    if t in (3, 4):
        return o + 4
    if t == 5:
        return o + 1
    if 11 <= t <= 15:
        n = struct.unpack_from('<I', v, o)[0]
        o += 4
        for _ in range(n):
            o = _skip_property(v, o, t - 10)
        return o
    raise ValueError(f'VMAD property type {t}')

"""Skyrim BSA reader (v104, zlib) for Enderal LE's archives: list and extract files."""
import struct, sys, zlib
from pathlib import Path
import tes5

DATA = Path(tes5.DATA['le'])
EMBED_NAMES = 0x100
COMPRESSED = 0x4


def entries(path):
    with open(path, 'rb') as f:
        magic, ver, off, aflags, nfold, nfile, _, fnl_files, _ = struct.unpack('<4s8I', f.read(36))
        assert ver == 104, f'{path.name}: BSA v{ver}; only LE archives (v104) are supported'
        folders = [struct.unpack('<QII', f.read(16)) for _ in range(nfold)]
        recs = []
        for _, cnt, _ in folders:
            dname = f.read(f.read(1)[0])[:-1].decode('latin1')
            for _ in range(cnt):
                _, size, foff = struct.unpack('<QII', f.read(16))
                recs.append((dname, size, foff))
        names = f.read(fnl_files).split(b'\0')
        for (dname, size, foff), n in zip(recs, names):
            compressed = bool(aflags & COMPRESSED) != bool(size & 0x40000000)
            yield f'{dname}\\{n.decode("latin1")}', size & 0x3FFFFFFF, foff, compressed, bool(aflags & EMBED_NAMES)


def read(path, size, foff, compressed, embedded):
    with open(path, 'rb') as f:
        f.seek(foff)
        blob = f.read(size)
    if embedded:
        blob = blob[1 + blob[0]:]
    return zlib.decompress(blob[4:]) if compressed else blob


_index = None


def index():
    global _index
    if _index is None:
        _index = {}
        for p in sorted(DATA.glob('*.bsa')):
            for name, *rest in entries(p):
                _index.setdefault(name.lower(), (p, *rest))
    return _index


def extract(name):
    hit = index().get(name.lower().replace('/', '\\'))
    return read(*hit) if hit else None


if __name__ == '__main__':
    if sys.argv[1] == 'ls':
        for name, (p, *_) in index().items():
            if all(k in name for k in sys.argv[2].lower().split()):
                print(p.name, name)
    elif sys.argv[1] == 'x':
        b = extract(sys.argv[2])
        Path(sys.argv[3]).write_bytes(b)
        print(len(b))

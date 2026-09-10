"""Read-only ISO9660 input inventory and deterministic source snapshots."""
import hashlib
import json
import struct
from pathlib import Path

SECTOR = 2048


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(obj, indent=2, ensure_ascii=True) + '\n').encode())


class Disc:
    def __init__(self, path, runtime=False):
        self.path = Path(path).resolve()
        self.size = self.path.stat().st_size
        self.entries = {}
        self.directories = set()
        with self.path.open('rb') as f:
            f.seek(16 * SECTOR)
            pvd = f.read(SECTOR)
            if pvd[1:6] != b'CD001':
                raise ValueError('Expected 2048-byte ISO9660 image: %s' % path)
            root = pvd[156:190]
            self._walk(f, struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0], '')
        self.runtime = {}
        if 'VMAP.DAT' in self.entries:
            vmap = self.read('VMAP.DAT')
            for off in range(0, len(vmap) - 47, 48):
                raw = vmap[off:off + 40].split(b'\0')[0]
                if not raw.startswith(b'\\\\'):
                    continue
                name = raw.decode('ascii').replace('\\\\', '/').lstrip('/').split(';')[0]
                lba, sectors = struct.unpack_from('<II', vmap, off + 40)
                self.runtime[name] = dict(lba=lba, sectors=sectors, vmap_offset=off)
                if runtime and name in self.entries:
                    old = self.entries[name]
                    if lba != old['lba'] or sectors * SECTOR < old['size']:
                        self.entries[name] = dict(old, iso_lba=old['lba'], iso_size=old['size'], lba=lba, size=sectors * SECTOR, runtime_override=True)

    def _walk(self, f, lba, size, parent):
        if (lba, size) in self.directories:
            return
        self.directories.add((lba, size))
        f.seek(lba * SECTOR)
        data = f.read(size)
        pos = 0
        while pos < len(data):
            length = data[pos]
            if not length:
                pos = (pos // SECTOR + 1) * SECTOR
                continue
            rec = data[pos:pos + length]
            if len(rec) < 34:
                raise ValueError('Malformed ISO directory')
            raw = rec[33:33 + rec[32]]
            if raw not in (b'\0', b'\1'):
                name = raw.decode('ascii').split(';')[0]
                path = (parent + '/' + name).lstrip('/')
                start, count = struct.unpack_from('<I', rec, 2)[0], struct.unpack_from('<I', rec, 10)[0]
                if rec[25] & 2:
                    self._walk(f, start, count, path)
                else:
                    if start * SECTOR + count > self.size:
                        raise ValueError('Member outside ISO: ' + path)
                    self.entries[path] = dict(lba=start, size=count, directory_record=lba * SECTOR + pos)
            pos += length

    def read(self, name):
        e = self.entries[name]
        with self.path.open('rb') as f:
            f.seek(e['lba'] * SECTOR)
            data = f.read(e['size'])
        if len(data) != e['size']:
            raise ValueError('Short member read: ' + name)
        return data

    def fingerprints(self):
        result = {}
        with self.path.open('rb') as f:
            for name, e in self.entries.items():
                h = hashlib.sha256()
                f.seek(e['lba'] * SECTOR)
                left = e['size']
                while left:
                    part = f.read(min(left, 8 << 20))
                    if not part:
                        raise ValueError('Short input read')
                    h.update(part)
                    left -= len(part)
                result[name] = dict(e, sha256=h.hexdigest())
        return result


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda: f.read(8 << 20), b''):
            h.update(part)
    return h.hexdigest()


def snapshot(original, best, english, out):
    from concurrent.futures import ThreadPoolExecutor
    out = Path(out)
    if (out/'inputs.json').exists():
        raise ValueError('Snapshot already exists; use a new work directory for a translation update')
    discs = {k: Disc(v, runtime=(k == 'english')) for k, v in [('original', original), ('best', best), ('english', english)]}
    expected = {
        'original': ('SLPS_258.87', '6c4c81c4e5aa3db1f52d70b8183ce11c01fc6b265ae4d53fa4d6a657c5019b50'),
        'best': ('SLPS_732.70', '3a3dcd48565d826de04718b227b59184db28f0cd969f594c77dfd2f12492f5bb'),
    }
    for edition, (name, digest) in expected.items():
        if sha(discs[edition].read(name)) != digest:
            raise ValueError('Wrong native executable: ' + edition)
    if discs['original'].size!=3758358528 or file_sha(original)!='ddbedefc0061213c50928fb213a7fb277c0345f01dab7386adc0383638a78cd2':
        raise ValueError('Original source ISO does not match verified edition')
    if discs['best'].size != 3755081728 or file_sha(best) != '950e2759d0d7482387d97d6df31325d9e352097a23e0bb4724073d1538d8cf77':
        raise ValueError('Best source ISO does not match verified edition')
    print('Best ISO identity verified', flush=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = {k: pool.submit(d.fingerprints) for k, d in discs.items()}
        hashes = {k: j.result() for k, j in jobs.items()}
    changes = []
    if set(hashes['english'])!=set(hashes['original']):
        raise ValueError('English ISO membership changed; review new or removed assets')
    for name, a in hashes['original'].items():
        if name not in hashes['english']:
            raise ValueError('English source missing native member: ' + name)
        c = hashes['english'][name]
        bn = 'SLPS_732.70' if name == 'SLPS_258.87' else name
        b = hashes['best'][bn]
        if a['sha256'] != c['sha256'] and name != 'DMY/DMY.BIN':
            changes.append(dict(member=name, original=a['size'], best=b['size'], english=c['size'], native_same=a['sha256'] == b['sha256']))
            for edition, disc in discs.items():
                member = bn if edition == 'best' else name
                target = out / 'inputs' / edition / name
                target.parent.mkdir(parents=True, exist_ok=True)
                payload = disc.read(member)
                if sha(payload) != hashes[edition][member]['sha256']:
                    raise ValueError('Source changed during snapshot: ' + member)
                target.write_bytes(payload)
    # HEDBDY defines archive boundaries; save even when English is unchanged.
    for name in ['HEDBDY/HB.BIN', 'BTL/SRVC.SEG', 'SYSTEM.CNF']:
        for edition, disc in discs.items():
            target = out / 'inputs' / edition / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(disc.read(name))
    manifest = dict(sources={k: str(d.path) for k, d in discs.items()}, members=hashes, changed=changes)
    dump(out / 'inputs.json', manifest)
    print(json.dumps(changes, indent=2), flush=True)
    return manifest


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--original', required=True)
    p.add_argument('--best', required=True)
    p.add_argument('--english', required=True)
    p.add_argument('--out', required=True)
    args = p.parse_args()
    snapshot(args.original, args.best, args.english, args.out)

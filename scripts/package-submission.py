#!/usr/bin/env python3
"""Package the public source snapshot and private course supplement locally."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import stat
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/submission'
PUBLIC = OUT / 'heat-project-public.zip'
PRIVATE = OUT / 'heat-project-private-supplement.zip'
ORIGINALS = {
    '20261123T144518643559261Z-bundle-20261123T223214591911633Z.tar.gz':
        '74aad844b6976a44b169e964b2be98f8eb58125eed01534909cf2c695536ffc5',
    'parts23-20261120T231427Z-checked-20261121T022138Z.tar.gz':
        '5c62cc594070572f7a2a2b4fd5cae5485a89fef0b043f4766e2adaa9c0a175ff',
}


def listing(*options):
    output = subprocess.check_output(['git', 'ls-files', *options, '-z'], cwd=ROOT)
    return output.decode('utf-8').strip('\0').split('\0') if output else []


def add(archive, name, data, manifest, mode=0o644, prefix=''):
    member = ZipInfo(prefix + name)
    member.create_system = 3
    member.external_attr = (stat.S_IFREG | mode) << 16
    archive.writestr(member, data, compress_type=ZIP_DEFLATED)
    manifest.append(dict(file=name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))


def write_public(target):
    modes = {}
    for entry in listing('--stage'):
        metadata, name = entry.split('\t', 1)
        mode, _, stage = metadata.split()
        if stage != '0':
            raise ValueError(f'Resolve the Git conflict before packaging {name}')
        modes[name] = int(mode, 8)
    names = sorted(set(modes) | set(listing('--others', '--exclude-standard')))
    manifest = []
    with ZipFile(target, 'w', compression=ZIP_DEFLATED) as archive:
        for name in names:
            path = ROOT / name
            if not path.is_file():
                continue
            parts = Path(name).parts
            forbidden = {'.git', 'private', 'raw-private', '__pycache__'}
            if (path.is_symlink() or forbidden.intersection(parts) or parts[0] in ('output', 'build')
                    or parts[:2] == ('llm_log', 'raw')
                    or name.endswith(('.tar.gz', '.vdi', '.pem', '.key'))
                    or name in ('part0/config/hosts', 'part0/config/cluster.local.sh')):
                raise ValueError(f'Private, build or linked file unexpectedly selected by Git: {name}')
            add(archive, name, path.read_bytes(), manifest, modes.get(name, 0o644) & 0o777,
                prefix='heat-project/')
        archive.writestr('submission-manifest.json', json.dumps(dict(
            generated_utc=datetime.now(timezone.utc).isoformat(),
            scope='Public working-tree source and evidence snapshot. Use a Git checkout for cluster scripts.',
            files=manifest), indent=2))


def original_evidence():
    bundled = {}
    if PRIVATE.is_file():
        with ZipFile(PRIVATE) as previous:
            hashes = {r['file']: r['sha256']
                      for r in json.loads(previous.read('private-supplement-manifest.json'))}
            for name in ORIGINALS:
                member = 'original-evidence/' + name
                if member in hashes:
                    data = previous.read(member)
                    if hashlib.sha256(data).hexdigest() != hashes[member]:
                        raise ValueError(f'Original evidence in the existing supplement is damaged: {name}')
                    bundled[name] = data
    for name, expected_hash in ORIGINALS.items():
        data = bundled.get(name)
        if data is None:
            source = Path.home() / 'Downloads' / name
            try:
                data = source.read_bytes()
            except OSError as error:
                raise ValueError(f'Original evidence is needed here or in the existing private ZIP: {source}') from error
        if hashlib.sha256(data).hexdigest() != expected_hash:
            raise ValueError(f'Original evidence differs from the reviewed hash: {name}')
        yield 'original-evidence/' + name, data


def write_private(target):
    manifest = []
    with ZipFile(target, 'w', compression=ZIP_DEFLATED) as archive:
        for name, data in original_evidence():
            add(archive, name, data, manifest, mode=0o600)
        for path in sorted((ROOT / 'llm_log/private').rglob('*')):
            if path.is_file() and not path.is_symlink() and (
                    path.name == 'visible-messages.json' or path.name.endswith('.visible.jsonl')
                    or (path.name == 'manifest.json' and 'recovered' in path.parts)):
                add(archive, path.relative_to(ROOT).as_posix(), path.read_bytes(), manifest, mode=0o600)
        for name in ('AGENTS.md', 'llm_log/LOG.md', 'llm_log/README.md'):
            add(archive, name, (ROOT / name).read_bytes(), manifest, mode=0o600)
        archive.writestr('READ-ME-FIRST.txt',
                         'PRIVATE COURSE SUPPLEMENT. Share privately with the instructor.\n'
                         'Includes the original Parts 2/3 and 4 evidence and available visible AI records.\n'
                         'Every member must check for missing complete project conversations and metadata.\n'
                         'See recovery manifests for overlapping snapshots, compaction and missing attachments.\n')
        archive.writestr('private-supplement-manifest.json', json.dumps(manifest, indent=2))


def package():
    OUT.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=OUT) as temp:
        public = Path(temp) / PUBLIC.name
        private = Path(temp) / PRIVATE.name
        write_public(public)
        write_private(private)
        for path in (public, private):
            with ZipFile(path) as archive:
                if member := archive.testzip():
                    raise ValueError(f'ZIP integrity check failed for {member}')
        private.replace(PRIVATE)
        public.replace(PUBLIC)
    print('Public hand-in snapshot:', PUBLIC)
    print('Private supplement (all-member AI completeness still unverified):', PRIVATE)


if __name__ == '__main__':
    package()

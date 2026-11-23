#!/usr/bin/env python3
"""Export the working tree's public hand-in and a labelled private supplement.

No Git commit/push or VM work. Git's tracked/unignored file list defines the
public snapshot; private logs and original evidence are never force-added.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/submission'
PUBLIC=OUT/'heat-project-public.zip'
PRIVATE=OUT/'heat-project-private-supplement.zip'


def package():
    OUT.mkdir(parents=True,exist_ok=True)
    result=subprocess.run(['git','ls-files','--cached','--others','--exclude-standard','-z'],
                          cwd=ROOT,check=True,capture_output=True)
    names=sorted(set(result.stdout.decode('utf-8').split('\0'))-{''})
    manifest=[]
    with zipfile.ZipFile(PUBLIC,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name in names:
            path=ROOT/name
            if not path.is_file():continue
            parts=Path(name).parts
            if any(part in ('.git','private','raw-private','__pycache__') for part in parts) or parts[0] in ('output','build'):
                raise ValueError('Private/build path unexpectedly selected by Git: '+name)
            if name.endswith(('.tar.gz','.vdi','.pem','.key')) or name in ('part0/config/hosts','part0/config/cluster.local.sh'):
                raise ValueError('Private evidence/configuration unexpectedly selected: '+name)
            data=path.read_bytes()
            archive.writestr('heat-project/'+name,data)
            manifest.append(dict(file=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
        archive.writestr('submission-manifest.json',json.dumps(dict(
            generated_utc=datetime.now(timezone.utc).isoformat(),
            scope='Public working-tree snapshot including reviewed current delivery; archive of project sources, not a new Git commit.',
            files=manifest),indent=2))
    original_names=['20261123T144518643559261Z-bundle-20261123T223214591911633Z.tar.gz',
                    'parts23-20261120T231427Z-checked-20261121T022138Z.tar.gz']
    private_manifest=[]
    with zipfile.ZipFile(PRIVATE,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        def add(path,name):
            data=path.read_bytes();archive.writestr(name,data)
            private_manifest.append(dict(file=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
        for name in original_names:
            path=Path.home()/'Downloads'/name
            if not path.is_file():raise ValueError('Required original evidence archive missing: '+name)
            add(path,'original-evidence/'+name)
        # Export only known visible-message formats and recovery manifests.
        # Unfiltered agent session/tool/reasoning JSONL files are not copied.
        for path in sorted((ROOT/'llm_log/private').rglob('*')):
            if path.is_file() and (path.name=='visible-messages.json' or path.name.endswith('.visible.jsonl')
                                   or (path.name=='manifest.json' and 'recovered' in path.parts)):
                add(path,path.relative_to(ROOT).as_posix())
        for name in ['AGENTS.md','llm_log/LOG.md','llm_log/README.md']:
            add(ROOT/name,name)
        archive.writestr('READ-ME-FIRST.txt',
            'PRIVATE COURSE SUPPLEMENT - do not publish.\n'
            'Contains original Parts2/3 and Part4 evidence, known local visible-message snapshots and current visible records.\n'
            'This does NOT certify complete AI history across all three members, tools or computers.\n'
            'Each member must add any missing full project conversations and actual member/tool/model/date metadata.\n'
            'Recovered snapshots overlap; compaction and missing attachments are documented in their manifests.\n'
            'Unfiltered tool/hidden-reasoning session files are intentionally not copied.\n')
        archive.writestr('private-supplement-manifest.json',json.dumps(private_manifest,indent=2))
    print('Public hand-in snapshot:',PUBLIC)
    print('Private supplement (all-member AI completeness still unverified):',PRIVATE)
    for path in [PUBLIC,PRIVATE]:
        print(path.name,'bytes',path.stat().st_size,'SHA256',hashlib.sha256(path.read_bytes()).hexdigest())


if __name__=='__main__':package()

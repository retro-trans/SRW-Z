"""Build an English Best-edition test patch from a current Original English ISO."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
import archive_probe,data,disc,elf,elfmap,image,pack,stage,subtitles,verify


def validate_snapshot(root):
    manifest=json.loads((root/'inputs.json').read_text(encoding='utf-8'))
    for p in (root/'inputs').rglob('*'):
        if not p.is_file():continue
        version,name=p.relative_to(root/'inputs').as_posix().split('/',1)
        member='SLPS_732.70' if version=='best' and name=='SLPS_258.87' else name
        if disc.file_sha(p)!=manifest['members'][version][member]['sha256']:
            raise ValueError('Snapshot file changed: '+str(p))
    return manifest


def make_patch(source,output,patch,xdelta,work):
    source=Path(source).resolve();output=Path(output).resolve();patch=Path(patch).resolve()
    if patch.exists():raise ValueError('Patch already exists; choose a new filename')
    if not output.is_file() or not source.is_file():raise ValueError('Patch input missing')
    partial=patch.with_name(patch.name+'.partial')
    if partial.exists():raise ValueError('Partial patch already exists')
    patch.parent.mkdir(parents=True,exist_ok=True)
    executable=str(Path(xdelta).resolve())
    print('Encoding xdelta against the unmodified Japanese Best ISO',flush=True)
    subprocess.run([executable,'-e','-9','-S','none','-s',str(source),str(output),str(partial)],check=True)
    check=Path(work)/'xdelta-roundtrip.iso'
    if check.exists():raise ValueError('Round-trip verification output already exists')
    print('Decoding xdelta for byte-for-byte verification',flush=True)
    subprocess.run([executable,'-d','-s',str(source),str(partial),str(check)],check=True)
    expected=disc.file_sha(output);actual=disc.file_sha(check)
    if actual!=expected:raise ValueError('Xdelta round-trip hash mismatch')
    check.unlink()  # Only the exact scratch file created by this invocation.
    partial.rename(patch)
    result=dict(path=str(patch),bytes=patch.stat().st_size,sha256=disc.file_sha(patch),
                source_sha256=disc.file_sha(source),output_sha256=actual,roundtrip_verified=True)
    disc.dump(Path(work)/'patch-verification.json',result)
    print('Verified xdelta:',patch,flush=True)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--original',type=Path,help='Unmodified Japanese Original ISO, SLPS-25887')
    p.add_argument('--best',type=Path,help='Unmodified Japanese Best ISO, SLPS-73270')
    p.add_argument('--english',type=Path,help='Current English Original-edition ISO')
    p.add_argument('--work',type=Path,required=True,help='Private per-build snapshot and cache directory')
    p.add_argument('--tools',type=Path,default=Path(__file__).resolve().parent.parent,help='SRW-Z repository tools directory')
    p.add_argument('--output',type=Path,help='New candidate ISO; omit for components and verification only')
    p.add_argument('--patch',type=Path,help='New xdelta against Japanese Best; requires --output and --xdelta')
    p.add_argument('--xdelta',type=Path,help='xdelta3 executable')
    p.add_argument('--resume',action='store_true',help='Rebuild the existing frozen snapshot, not newer source edits')
    p.add_argument('--workers',type=int,default=6)
    args=p.parse_args();root=args.work.resolve();tools_dir=args.tools.resolve()
    if args.patch and (not args.output or not args.xdelta):p.error('--patch requires --output and --xdelta')
    if not (tools_dir/'banlz.py').is_file():p.error('--tools must point to the SRW-Z repository tools directory')
    if args.work.resolve()==Path(__file__).resolve().parent:p.error('Keep generated work separate from adapter source')
    if args.resume:
        manifest=validate_snapshot(root)
        for key in ('original','best','english'):
            supplied=getattr(args,key)
            if supplied and supplied.resolve()!=Path(manifest['sources'][key]).resolve():p.error('--resume input paths differ from the frozen snapshot')
    else:
        if not all((args.original,args.best,args.english)):p.error('A new build requires --original, --best and --english')
        manifest=disc.snapshot(args.original,args.best,args.english,root)
    layout_path=Path(__file__).with_name('layout.json')
    layout=json.loads(layout_path.read_text(encoding='utf-8'))
    elfmap.analyze(*(root/'inputs'/v/'SLPS_258.87' for v in ('original','best','english')),directory=root/'elf_analysis',raw=True)
    port=elf.ElfPort(root,layout);port.build();port.save()
    archive_probe.run(root,tools_dir,layout_path)
    stage.run(root,tools_dir);subtitles.run(root,layout);data.run(root,tools_dir)
    pack.run(root,tools_dir,layout,args.workers)
    verify.run(root,tools_dir,layout)
    if args.output:
        output=image.assemble(root,args.output)
        if args.patch:make_patch(manifest['sources']['best'],output,args.patch,args.xdelta,root)
    print('Adapter build complete. Candidate requires emulator and PS2 hardware testing.',flush=True)


if __name__=='__main__':
    try:main()
    except (ValueError,OSError,subprocess.CalledProcessError) as exc:
        print('Build stopped: '+str(exc),file=sys.stderr);sys.exit(1)

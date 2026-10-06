#!/usr/bin/env python3
"""Hash completed capture files before/after lossless map gzip compression."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path


def digest(stream):
    result = hashlib.sha256()
    for block in iter(lambda:stream.read(1024*1024),b''):
        result.update(block)
    return result.hexdigest()


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('root',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--verify',type=Path)
    args=parser.parse_args()
    if args.verify:
        manifest=json.loads(args.verify.read_text())
        for relative,expected in manifest['sha256'].items():
            path=args.root/relative
            stream=path.open('rb') if path.is_file() else gzip.open(str(path)+'.gz','rb')
            with stream:
                if digest(stream)!=expected:
                    raise ValueError('capture content changed: '+relative)
        print(json.dumps(dict(verified=True,files=len(manifest['sha256']),lossless=True)))
        return
    if not args.output:
        parser.error('--output is required when sealing')
    hashes={}
    for path in sorted(args.root.rglob('*')):
        if path.is_file():
            if not (path.parent/'COMPLETE').is_file():
                raise ValueError('incomplete producer frame: '+str(path.parent))
            with path.open('rb') as stream:
                hashes[str(path.relative_to(args.root))]=digest(stream)
    with args.output.open('x') as stream:
        json.dump(dict(schema='planner-capture-original-sha256-v1',sha256=hashes),stream,indent=2)
        stream.write('\n')
    print(json.dumps(dict(sealed_files=len(hashes))))


if __name__=='__main__':
    main()

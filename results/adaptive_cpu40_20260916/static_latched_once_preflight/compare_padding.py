#!/usr/bin/env python3
"""Compare captured wire bytes without changing either input or acceptance SHA."""
import hashlib
import json
from pathlib import Path
import numpy as np

root = Path(__file__).resolve().parent
arrays = {mode: np.frombuffer((root / f'{mode}_padding_diagnostic_attempt1/first_payload.bin').read_bytes(),
                             dtype=np.uint8).reshape(-1, 32)
          for mode in ('full', 'standalone')}
full, standalone = arrays['full'], arrays['standalone']
out = dict(points=int(len(full)), different_bytes_by_offset=(full != standalone).sum(axis=0).tolist(),
           first20_bytes_exact=bool(np.array_equal(full[:, :20], standalone[:, :20])), modes={})
for mode, data in arrays.items():
    canonical = data.copy()
    canonical[:, 20:] = 0
    declared = np.concatenate([data[:, :12], data[:, 16:20]], axis=1)
    out['modes'][mode] = dict(raw_sha256=hashlib.sha256(data.tobytes()).hexdigest(),
        canonical_sha256=hashlib.sha256(canonical.tobytes()).hexdigest(),
        xyzi_sha256=hashlib.sha256(declared.tobytes()).hexdigest(),
        nonzero_tail_bytes=int(np.count_nonzero(data[:, 20:])))
print(json.dumps(out, indent=2))

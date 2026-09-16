# C18 first Full transport failure: wire padding, not changed geometry

Original standalone reader-first and late arms passed. The first Full
reader-first arm failed the fixed entire-payload SHA gate (a0f56169...). It was
not retried for a lucky success; all subsequent matrix arms were stopped.
A separate instrumented no-flight diagnostic retained the first received wire
payload before the same strict check. Full failed again with19a9bece..., while
standalone passed with the original b3064409... reference. Neither failed
attempt is relabeled a pass. Both exited cleanly, with no flight goals.

`compare_padding.py` and `padding_diagnosis.json` compare the exact captured
241490-by32-byte buffers. All first20 bytes of every point match bit-for-bit:
XYZ, homogeneous value and intensity. Exactly76 bytes differ, exclusively at
offsets20..31. Standalone's tail is all zero. Both declared-field SHA values are
`9f1846e0a3f0172d1a4db698f357aa0a8007e005d3d5597ee288a7e0442a2767`.
Setting only these unused tail bytes to zero produces the original entire-wire
SHA `b3064409563b3d41cdc5f982a058b2df7a776627cae7cf367086176bccd6439f`
for both captures. No numerical tolerances or sorted/reordered comparison used.

Installed PCL1.12 `pcl/impl/point_types.hpp:520` initializes XYZ, data[3] and
intensity but not final union bytes. `pcl/conversions.h:255` explicitly memcpy's
the complete struct, including padding. The map loader reads XYZ-only ASCII
PCD into PointXYZI; `getGlobalMap` returns an exact cloud copy. This explains the
process-dependent raw hash without asserting all future differences harmless.

Fix only the opt-in one-shot wire copy: verify exact XYZI metadata and32-byte
stride, zero offsets20..31, retain the first20 bytes/order/size exactly. Do not
modify renderer geometry, sensor scans, legacy serialization, PCD, planner or
safety logic. Keep the original full-wire SHA gate unchanged. Optimized and
ASan/UBSan helper tests now39 checks, including prefix preservation, malformed
input rejection before mutation, and idempotence.

Rebuild production, then rerun all six transport combinations under fresh
`*_canonical_attempt1` directories, followed by actual RViz and CPU tests.
The pre-repair successful standalone tests cannot substitute for final-build
validation. `.bin` captures remain local diagnostic artifacts; source hashes,
JSON outcomes, comparison program and logs are retained with this record.

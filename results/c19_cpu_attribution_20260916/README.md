# C19 CPU attribution: execution complete, expansion gate FAILED

All six seed1 flights (Full/Sector/Adaptive × profiler ON/OFF) completed with
zero measured contacts and no flight retries. Source/recovery/resource/speed
contracts pass. However, OFF Adaptive43.75s / Full37.67s =1.1614 **fails** the
predeclared1.10 paired mission-time limit. Do not mistake controller COMPLETE,
report-parser warnings=0, or contact-free completion for all-gates acceptance.

- Definitive audit: [verification.json](verification.json), all gates=false.
- Explanation and next step: [Korean report](../../docs/c19_cpu_attribution_and_map_freeze_20260916.md).
- Exclusive function subtotals, simulator and unclassified accounting:
  [attribution/README.md](attribution/README.md). Not complete autonomy CPU.
- OFF/ON metric groups: [comparison/summary_ko.md](comparison/summary_ko.md).
- Preregistered run order and runtime hashes: [plan.json](plan.json).
- Static-map transport/RViz evidence: [static_preflight/acceptance.json](static_preflight/acceptance.json).
- Original C19 source snapshot: preservation/c19_pre_attribution_sources.tar.gz,
  SHA2569351ec52b639c4a43d0f6d59d2ded17c4cc1f2007e8e602ccc182f93deda1052.

OFF Adaptive entered Full recovery4times versus1ON; all4 finished. Two extra
episodes show VERSION_CHANGED while a new trajectory is committed, followed by
conservative braking. Another includes UNOBSERVED/dynamics brake rejection.
All evidence is retained; no tuning or lucky-run replacement was performed.
Single ON/OFF flights do not identify profiler overhead. Old frozen OFF n5 is
preserved separately and is not pooled. No20/map expansion campaign was run.

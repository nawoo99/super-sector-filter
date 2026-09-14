#!/usr/bin/env python3
"""Stop our exact controller after a completed three-mode block, not mid-flight.

An explicit logged futility stop, never a retry or a replacement of failed
rows. The original confirmation runner/freeze/raw remain resumable unchanged.
"""
import argparse
import csv
import ctypes
import json
import os
from pathlib import Path
import signal
import select
import time

import confirm_cylinder_search_n20 as confirmation


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map")
    parser.add_argument("--pid",type=int,required=True)
    parser.add_argument("--after-run",type=int,required=True)
    args=parser.parse_args()
    folder=confirmation.ROOT/args.map
    expected=["python3","scripts/native_campaign/confirm_cylinder_search_n20.py",args.map]
    command=Path(f"/proc/{args.pid}/cmdline")
    def validate_pid():
        actual=command.read_bytes().decode().strip("\0").split("\0")
        if actual!=expected:
            raise RuntimeError(f"Refusing to signal non-matching controller: {actual}")
    validate_pid()
    marker=folder/"boundary_stop.json"
    if marker.exists():
        raise RuntimeError("A boundary stop is already recorded")
    # Wait for kernel file-write notifications instead of repeatedly parsing
    # the CSV during flight, so boundary supervision uses negligible CPU.
    libc=ctypes.CDLL(None,use_errno=True)
    notification=libc.inotify_init1(os.O_NONBLOCK|os.O_CLOEXEC)
    if notification<0 or libc.inotify_add_watch(notification,
            ctypes.c_char_p(os.fsencode(folder/"raw.csv")),2|8)<0:
        raise OSError(ctypes.get_errno(),"Cannot watch raw result writes")
    while True:
        validate_pid()
        rows=list(csv.DictReader((folder/"raw.csv").open()))
        keys={(int(r["run"]),r["mode"]) for r in rows if r.get("run") and r.get("mode")}
        required={(r,m) for r in range(101,args.after_run+1) for m in confirmation.MODES}
        complete_blocks=(len(rows)==len(keys) and len(rows)%3==0 and required<=keys
                         and all((r,m) in keys for r,_ in keys for m in confirmation.MODES))
        valid=all(confirmation.known_outcome(r) for r in rows)
        # A ready file without its finalized observer report means a flight
        # may already be active. Never interrupt it to make a clean-looking row.
        inflight=any(not p.with_name(p.name.replace(".ready.json",".json")).exists()
                     for p in (folder/"solid").glob("*.ready.json"))
        if complete_blocks and valid and not inflight:
            failed=[{k:r[k] for k in ("map","run","mode","success","solid_collision_episodes")}
                    for r in rows if r["mode"] in ("full","adaptive") and not confirmation.safe(r)]
            if not failed:
                raise RuntimeError("Refusing futility stop without an actual reference failure")
            validate_pid()
            os.kill(args.pid,signal.SIGINT)
            record=dict(action="SIGINT_exact_own_controller_at_completed_block_boundary",
                        epoch_s=time.time(),pid=args.pid,completed_rows=len(rows),planned_rows=60,
                        reason="Both reference safety/completion perfection and the observed user criterion are no longer attainable on this frozen confirmation",
                        reference_failures=failed,raw_rows_deleted_or_replaced=False,
                        completed_20_per_mode=False,original_freeze_unchanged=True,
                        resumption="Original confirmation runner can resume the same frozen rows if requested")
            marker.write_text(json.dumps(record,indent=2)+"\n")
            print(json.dumps(record),flush=True)
            return
        if select.select([notification],[],[],1.)[0]:
            os.read(notification,65536)


if __name__=="__main__":
    main()

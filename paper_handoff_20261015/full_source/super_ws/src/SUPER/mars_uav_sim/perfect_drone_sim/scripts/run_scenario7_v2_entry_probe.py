#!/usr/bin/env python3
"""Single diagnostic of unchanged guard-v2 at the actual first-entry ROI.

The old probe and all binary/source assets remain frozen. This adapter only
selects v2 identity, the already-recorded contact surface, and diagnostic labels.
Trace loss/truncation still limits causal interpretation; never a primary run.
"""
from pathlib import Path
import inspect
from types import SimpleNamespace

import run_scenario7_contact_probe as prior
import run_scenario7_guard_v2 as controller
import scenario7_guard_v2_cpu_compare as child

PRIOR_SHA256 = 'bd8da40d99d1da8df89cb514ae510705e98a2318ca31a01b0dceeb011d4663ca'
CHILD_SHA256 = 'a045b9aa00bfcd2f882a6e77312deb0b35978d15c44ac867f14cde61bca4fa81'
ROOT = Path('/root/super-sector-filter/results/scenario7_guard_contract_smoke_20260926_v2b')
INVENTORY_SHA256 = 'bf2fd286f18231f8761507d56ceed9cbf71b4bea689cd6baf7742571f3df98b1'


def build_probe():
    if prior.sha(prior.__file__) != PRIOR_SHA256 or prior.sha(child.__file__) != CHILD_SHA256:
        raise ValueError('Frozen diagnostic dependencies changed')
    module = controller.previous.runtime.clone_module(prior)
    module.__file__ = str(Path(__file__).resolve())
    module.__doc__ = __doc__
    module.SCHEMA = 'scenario7-v2-first-entry-diagnostic-v1'
    module.V1_ROOT = ROOT
    module.V1_INVENTORY = ROOT / 'frozen_inputs_and_evidence.json'
    module.V1_INVENTORY_SHA256 = INVENTORY_SHA256
    module.CHILD_SHA256 = CHILD_SHA256
    module.controller = SimpleNamespace(**vars(controller), sha=controller.previous.sha)
    module.ROIS = {
        'urban_blocks_u01': dict(name='building_10_east_face', center_x=-4., center_y=3.5),
        'gapfree_d1_m04': dict(name='cylinder_0040', center_x=-18.556532, center_y=-.319020),
    }

    def build_main(*, source_transform, namespace_updates):
        # Compose both explicit observation labels and the unchanged revision-2
        # policy audit. The profile-reference path is forbidden by the probe.
        def transform(source):
            return source_transform(child.adapt_main(source))
        return child.previous.build_main(
            install_root=child.DEFAULT_INSTALL, source_transform=transform,
            namespace_updates=dict(namespace_updates, policy_audit=child.policy_audit,
                POLICY_REVISION=child.POLICY_REVISION, STOP_POLICY=child.STOP_POLICY,
                GUARD_CHILD_SOURCE=Path(child.__file__).resolve()))

    module.child = SimpleNamespace(__file__=child.__file__, previous=child.previous.previous,
                                   build_main=build_main)
    # Inherited field names frozen_v1_inventory remain compatibility labels;
    # their values bind the exact v2 inventory above. Repair the human-facing
    # runtime/candidate labels in private functions, never in the old file.
    for name in ('main', 'flight_arguments'):
        source = inspect.getsource(getattr(prior, name))
        old = 'repair_v1_unchanged' if name == 'main' else 'contact_probe_repair_v1'
        new = 'guard_v2_unchanged' if name == 'main' else 'contact_probe_guard_v2'
        if source.count(old) != 1:
            raise ValueError('Diagnostic adaptation cardinality changed: ' + name)
        exec(compile(source.replace(old, new, 1), str(Path(__file__).resolve()), 'exec'),
             module.__dict__)
    return module


if __name__ == '__main__':
    raise SystemExit(build_probe().main())

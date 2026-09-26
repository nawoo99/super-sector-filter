import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import run_scenario7_v2_entry_probe as probe
import run_scenario7_contact_probe as prior


class ProbeBindingTests(unittest.TestCase):
    def test_private_globals_and_unmodified_legacy(self):
        module = probe.build_probe()
        self.assertIsNot(module, prior)
        self.assertNotEqual(module.V1_ROOT, prior.V1_ROOT)
        self.assertEqual(module.V1_ROOT, probe.ROOT)
        self.assertEqual(module.sha(probe.__file__), prior.sha(probe.__file__))
        self.assertEqual(module.main.__globals__, vars(module))

    def test_roi_and_trace_caps(self):
        module = probe.build_probe()
        trace = module.trace_settings(Path('/tmp/diagnostic-fixture'), 'urban_blocks_u01')
        self.assertEqual(trace['roi']['center_x'], -4.)
        self.assertEqual(trace['roi']['center_y'], 3.5)
        self.assertEqual(trace['roi']['file_cap_bytes'], prior.FILE_CAP)
        self.assertNotIn('gapfree_d1_m01', module.ROIS)

    def test_child_composition_keeps_diagnostic_labels_and_policy_audit(self):
        module = probe.build_probe()
        main = module.child.build_main(source_transform=module.adapt_child,
            namespace_updates={'PROBE': {'schema': module.SCHEMA}})
        self.assertEqual(main.__globals__['POLICY_REVISION'], 2)
        self.assertEqual(str(main.__globals__['repair_runtime'].install),
                         str(probe.child.DEFAULT_INSTALL))
        self.assertIn('diagnostic_only', main.__code__.co_consts)

    def test_legacy_bytes_remain_pinned(self):
        self.assertEqual(prior.sha(prior.__file__), probe.PRIOR_SHA256)
        self.assertEqual(prior.sha(probe.child.__file__), probe.CHILD_SHA256)


if __name__ == '__main__':
    unittest.main()

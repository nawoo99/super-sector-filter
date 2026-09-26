#!/usr/bin/env python3
"""Private runtime bindings for the separately built scenario7 repair cohort.

The original install remains an underlay and is still inventoried. Only the
three explicitly rebuilt packages resolve to the new overlay. No imported
legacy module globals, bytecode, files, or thresholds are modified in place.
"""
from __future__ import annotations

import importlib.util
import inspect
import os
from pathlib import Path
import shlex
import sys
import types

import scenario7_cpu_compare as previous

BASE_INSTALL = Path('/root/super_ws/install')
DEFAULT_INSTALL = Path('/root/super_ws/scenario7_repair_20260926/install')
PACKAGES = frozenset({'rog_map', 'super_planner', 'perfect_drone_sim'})
PINNED_MODULES = {
    'normal_cpu_gpu_diagnostic': '3a4d3721b3a4933ce3a57521ed3217eb97b1a98c0bab85a31049b6ee758c6aa1',
    'cylinder_map_search': 'ad8e9e3fcec7111aaa3e015e02844f8c3c3df4a1227e3f906199419cb39a7ae0',
    'native_campaign': previous.mission_runtime.CAMPAIGN_SHA256,
    'static_latched_preflight': '917aaac77016a0867ac3a47fd0926cbc9846258f4fe26dbf3be1b0cf44779892',
}
FIXTURES = {
    'transport': ('static_pc_late_subscriber_test.py',
                  'a8a1e1b76fe44f134485f6a79f7907b1d83186bfcfc98845da31780cf79fd108'),
    'rviz': ('static_map_rviz_reconnect_test.py',
             '034c46dfcb80dd2e9761ba35332781ea37d0adf90c2078d5879cdd9308494987'),
}


def clone_module(module):
    """Rebind owned Python functions/classes to a new module namespace."""
    expected = PINNED_MODULES.get(module.__name__)
    if expected is not None and previous.support.sha256(module.__file__) != expected:
        raise ValueError('Frozen overlay dependency changed: ' + module.__name__)
    clone = types.ModuleType(module.__name__)
    clone.__dict__.update(vars(module))
    namespace = clone.__dict__

    def function(value):
        result = types.FunctionType(value.__code__, namespace, value.__name__,
                                    value.__defaults__, value.__closure__)
        result.__kwdefaults__ = value.__kwdefaults__
        result.__annotations__ = value.__annotations__.copy()
        result.__dict__.update(value.__dict__)
        result.__qualname__ = value.__qualname__
        return result

    for name, value in list(namespace.items()):
        if isinstance(value, types.FunctionType) and value.__globals__ is vars(module):
            namespace[name] = function(value)
    for name, value in list(namespace.items()):
        # C/ctypes classes (GPU structures) and external classes stay unchanged.
        if (isinstance(value, type) and value.__module__ == module.__name__
                and type(value) is type):
            attributes = {key: item for key, item in vars(value).items()
                          if key not in ('__dict__', '__weakref__')}
            for key, item in list(attributes.items()):
                if isinstance(item, types.FunctionType) and item.__globals__ is vars(module):
                    if '__class__' in item.__code__.co_freevars:
                        raise ValueError('Class closure requires explicit overlay review: ' + name)
                    attributes[key] = function(item)
                elif isinstance(item, (staticmethod, classmethod)):
                    underlying = item.__func__
                    if underlying.__globals__ is vars(module):
                        attributes[key] = type(item)(function(underlying))
            namespace[name] = type(name, value.__bases__, attributes)
    return clone


class RuntimeBinding:
    def __init__(self, install_root=DEFAULT_INSTALL):
        selected = Path(install_root)
        self.install = selected.resolve()
        if not selected.is_absolute() or self.install.is_relative_to(BASE_INSTALL.resolve()):
            raise ValueError('Repair cohort requires a separate absolute install prefix')

    def select_path(self, path):
        path = Path(path)
        try:
            relative = path.relative_to(BASE_INSTALL)
        except ValueError:
            return path
        if relative.parts and relative.parts[0] in PACKAGES:
            return self.install / relative
        return path

    def asset_paths(self):
        required = {
            self.install / 'local_setup.bash', self.install / 'setup.bash',
            self.install / 'rog_map/lib/librog_map.a',
            self.install / 'super_planner/lib/libsuper.a',
            self.install / 'super_planner/lib/super_planner/fsm_node',
            *(self.install / 'perfect_drone_sim/lib/perfect_drone_sim' / name for name in
              ('perfect_drone_node', 'perfect_drone_full_node', 'perfect_drone_adaptive_node')),
        }
        for package in PACKAGES:
            required.add(self.install / package / 'share/ament_index/resource_index/packages' / package)
        missing = sorted(str(path) for path in required if not path.is_file())
        if missing:
            raise ValueError('Repair overlay is incomplete: ' + ', '.join(missing))
        # Bind package selection hooks, launch/config assets, executables and
        # libraries, not just the binaries singled out by the old child.
        assets = {path for path in self.install.rglob('*')
                  if path.is_file() and '__pycache__' not in path.parts
                  and path.suffix != '.pyc'}
        return assets | required | {Path(__file__).resolve()}

    def identity(self):
        return dict(schema='scenario7-repair-runtime-v1', install=str(self.install),
                    base_install=str(BASE_INSTALL), overlay_packages=sorted(PACKAGES),
                    assets_sha256={str(path): previous.support.sha256(path)
                                   for path in sorted(self.asset_paths())},
                    original_install_retained=True, not_pooled_with_previous_results=True)

    def map_context(self, map_name):
        value = previous.inherited.static_latched_preflight.map_context(map_name)
        value['paths'] = {key: self.select_path(path) for key, path in value['paths'].items()}
        return value

    def namespace(self):
        original = previous.inherited.diagnostic
        campaign = clone_module(original.search.campaign)
        campaign._ACTIVE_PROCESS_GROUPS = {}
        campaign.ROS_ENV = (campaign.ROS_ENV + ' && source ' +
                            shlex.quote(str(self.install / 'local_setup.bash')))
        search = clone_module(original.search)
        search.campaign = campaign
        base_policy = search.frozen_policy

        def frozen_policy():
            policy = base_policy()
            policy['scenario7_repair_runtime'] = self.identity()
            policy['sha256'].update(policy['scenario7_repair_runtime']['assets_sha256'])
            return policy

        search.frozen_policy = frozen_policy
        diagnostic = clone_module(original)
        diagnostic.search = search
        static = types.SimpleNamespace(**vars(previous.inherited.static_latched_preflight))
        static.map_context = self.map_context
        return dict(diagnostic=diagnostic, static_latched_preflight=static,
                    repair_runtime=self)

    def profile_reference_audit(self, plan, reference_plan, summaries):
        # Keep every original test, changing only its two executable inventory
        # targets in an isolated function. The metadata itself stays literal.
        legacy = previous.inherited.legacy
        source = inspect.getsource(legacy.small_pool_profile_reference_audit)
        old = "'/root/super_ws/install/perfect_drone_sim/lib/perfect_drone_sim/'"
        if source.count(old) != 1:
            raise ValueError('Required-binary reference audit adaptation changed')
        source = source.replace(old, repr(str(self.install / 'perfect_drone_sim/lib/perfect_drone_sim') + '/'))
        namespace = dict(vars(legacy))
        exec(compile(source, str(Path(__file__).resolve()), 'exec'), namespace)
        # The seven-map wrapper still adds all independent solid/map gates.
        wrapper_source = inspect.getsource(previous.small_pool_profile_reference_audit)
        old_call = 'inherited.legacy.small_pool_profile_reference_audit(plan, reference_plan, summaries)'
        if wrapper_source.count(old_call) != 1:
            raise ValueError('Seven-map reference wrapper adaptation changed')
        wrapper_source = wrapper_source.replace(old_call, 'legacy_audit(plan, reference_plan, summaries)')
        wrapper_namespace = dict(vars(previous), legacy_audit=namespace['small_pool_profile_reference_audit'])
        exec(compile(wrapper_source, str(Path(__file__).resolve()), 'exec'), wrapper_namespace)
        audit = wrapper_namespace['small_pool_profile_reference_audit'](plan, reference_plan, summaries)
        added = {key + '_match': key in plan and key in reference_plan
                 and plan[key] == reference_plan[key]
                 for key in ('scenario7_control_revision', 'scenario7_repair_runtime')}
        audit['checks'].update(added)
        audit['acceptance_checks'].update(added)
        audit['valid'] = audit['valid'] and all(added.values())
        return audit


def build_namespace(install_root=None):
    return RuntimeBinding(install_root or os.environ.get(
        'SCENARIO7_REPAIR_INSTALL', str(DEFAULT_INSTALL))).namespace()


def verify_package_selection(binding, get_package_prefix):
    """Require actual ament resolution to match the declared overlay."""
    for package in sorted(PACKAGES):
        actual = Path(get_package_prefix(package)).absolute()
        expected = binding.install / package
        if actual != expected:
            raise ValueError(f'Overlay package resolution mismatch: {package}: {actual} != {expected}')


def static_main(argv=None, *, install_root=None):
    previous.support.register_maps()
    binding = RuntimeBinding(install_root or os.environ.get(
        'SCENARIO7_REPAIR_INSTALL', str(DEFAULT_INSTALL)))
    static = clone_module(previous.inherited.static_latched_preflight)
    static.map_context = binding.map_context
    return static.main(argv)


def fixture_main(action, argv=None, *, install_root=None):
    """Run an unmodified, pinned no-flight fixture under a verified overlay.

    The controller must source the original setup and overlay/local_setup.bash
    before starting Python, so ROS imports and shared libraries agree as well.
    """
    binding = RuntimeBinding(install_root or os.environ.get(
        'SCENARIO7_REPAIR_INSTALL', str(DEFAULT_INSTALL)))
    binding.asset_paths()
    from ament_index_python.packages import get_package_prefix
    verify_package_selection(binding, get_package_prefix)
    name, expected = FIXTURES[action]
    path = previous.support.PACKAGE / 'test' / name
    if previous.support.sha256(path) != expected:
        raise ValueError('Frozen static fixture changed: ' + str(path))
    spec = importlib.util.spec_from_file_location('scenario7_repair_' + action, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    old_argv = sys.argv
    try:
        sys.argv = [str(path), *(sys.argv[2:] if argv is None else argv)]
        return module.main()
    finally:
        sys.argv = old_argv


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] not in ('static', 'transport', 'rviz'):
        raise SystemExit('Usage: scenario7_repair_runtime.py {static|transport|rviz} [fixture options]')
    if args[0] == 'static':
        return static_main(args[1:])
    return fixture_main(args[0], args[1:])


if __name__ == '__main__':
    raise SystemExit(main())

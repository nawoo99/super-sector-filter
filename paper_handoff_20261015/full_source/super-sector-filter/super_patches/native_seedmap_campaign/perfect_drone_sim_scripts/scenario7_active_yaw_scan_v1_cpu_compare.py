#!/usr/bin/env python3
"""Compatibility entrypoint for the canonical Active-Yaw Sector runner.

Active-Yaw is now the default behavior of ``scenario7_guard_v6_cpu_compare``.
This historical wrapper remains so archived commands keep working without
applying the Active-Yaw source transform twice.
"""
import scenario7_guard_v6_cpu_compare as canonical


verify_default_sector_contract = canonical.verify_default_sector_contract


def main():
    return canonical.main()


if __name__ == '__main__':
    raise SystemExit(main())

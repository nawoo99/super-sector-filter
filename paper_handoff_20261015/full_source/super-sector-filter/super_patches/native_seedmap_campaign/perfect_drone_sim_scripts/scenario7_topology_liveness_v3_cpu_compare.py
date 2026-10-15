#!/usr/bin/env python3
"""Retired V3 cohort entrypoint; historical diagnostic evidence is retained."""


def main():
    raise RuntimeError(
        'V3 cohort prefix is retired after the V4 build-cache migration. '
        'Retained diagnostic Full binaries/logs are evidence only; '
        'V4 broad confirmation requires passing all targeted recovery gates.')


if __name__ == '__main__':
    raise SystemExit(main())

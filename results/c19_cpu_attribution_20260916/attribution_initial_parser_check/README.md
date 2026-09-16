# Initial offline parser check (not a flight retry)

The first grouping pass incorrectly required `frontend_map_ack` in Fixed Sector.
The production constructor creates this subscription only for Adaptive with
generation ACK enabled. The pass stopped after saving alignment.json; no CPU
groups were accepted. The parser now checks mode-specific required scopes and
has a regression test. Verified output is in ../attribution/. Raw flight data
and runtime binaries were unchanged, and no flights were repeated.

# Read-only review before first C5 compilation

Reviewer: independent `cpu_savings_review` subagent. No runtime edits/builds
during the C4 flight freeze.

No unsafe default-cache acceptance identified. Confirmed weak control-block
ownership plus raw address/version identity, complete ordered neighbor content,
exact C4 raw-integer external predicate fields, collision verification, epoch
clearing and retained final-publication rejection.

One generic-template edge was fixed after freeze: `Epoch=bool` meets
integral/unsigned static assertions but cannot advance past true. It is now
explicitly rejected by a static assertion. Production default uint32_t was
never affected.

Additional prototype tests added from review:

- repeated cached occupied=true hit does not evaluate again;
- mutations at the middle and last entries of the full 257-neighbor sphere;
- returning from a bypassed query to the old context recomputes.

# Vantage contributor instructions

Read `PROJECT.md` and `docs/DECISIONS.md` before changing architecture or data semantics. Preserve source provenance and catalog-year boundaries. Default matching excludes optional courses and unverified evidence. Keep synthetic records visibly labeled and out of observed-market analytics. Keep database credentials server-only and application tables in the private schema.

When running shell commands, prefix commands with `rtk` where available. This environment initially did not have RTK installed; use an explicitly declared shell pass-through function named `rtk` when necessary, without claiming token optimization is active. Prefix each segment in command chains. For debugging, raw commands are allowed. `rtk proxy <cmd>` bypasses filtering when RTK is installed.

Run the checks documented in `README.md`. Database tests use an isolated local `_test` database; never point test fixtures at hosted data. Do not enable live collection without source review. Add a new migration rather than editing an applied migration.

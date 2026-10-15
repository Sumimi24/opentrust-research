# Minimal engineering replay: two networks, no model calls

This is an executable CPU replay example for OpenTrust. It includes a small
pandapower Kerber distribution network and the WNTR/EPANET Net1 water network,
their frozen task contracts, and existing initial/final designs. It is a
convenience sample for demonstrating reproducibility, not a new benchmark or
an additional estimate of model performance.

## Run

Use Python 3.12 and install the recorded dependencies:

```sh
python -m pip install -r requirements.txt
python run_demo.py
```

For the complete dependency set actually installed in the fresh Windows
Python 3.12 validation environment, use
`python -m pip install -r requirements-lock-windows-py312.txt` instead.
The lock is a complete `pip freeze` of application dependencies (bootstrap
pip version is recorded separately), not a cross-platform or wheel-hash lock.

The second command needs no network connection, API credential, model service,
GPU, original study directory or private configuration. Paths are resolved
relative to the example files, not your working directory. `engineering.py`
is copied byte-for-byte from the frozen study; it is not a new simulator.

The default run evaluates **four designs × sixteen scenarios = 64 scenario
evaluations**. Each design is checked on eight development and eight held
scenarios. A power scenario contains four AC power-flow snapshots. A water
scenario is a 48-hour EPANET simulation with 15-minute checking. The two power
designs are identical because the original model retained its initial design;
both stages are intentionally replayed.

Expected output:

```text
kerber_overhead initial: pass=True; scenarios=16; expected_match=True
kerber_overhead final: pass=True; scenarios=16; expected_match=True
Net1 initial: pass=False; scenarios=16; expected_match=True
Net1 final: pass=True; scenarios=16; expected_match=True
```

`results.json` contains actual measurements, constraint checks, stage labels,
comparison results, runtime and the machine/platform description. A frozen
replay mismatch produces a nonzero exit status. The reference observations are
not updated by the runner. A physically failing initial water design is an
expected result, not a replay failure.

## What is compared

The runner first verifies hashes of the unchanged simulator, source networks,
task contracts and extracted cases against `source_manifest.json`. It then
recomputes scores from the networks. Structural errors, solver failures,
scenario pass labels and individual constraint checks must match exactly.
Numeric measurements, including within-scenario trajectories retained in the
reference record, use absolute tolerance `1e-6` and relative tolerance `1e-8`
in their recorded units. Categorical fields must also match. These are replay
comparison tolerances and do not change the engineering acceptance rules.

Engineering acceptance tolerances remain those in the frozen code and tasks:
voltage `1e-6` pu, loading `1e-4` percentage points, water pressure/tank levels
`0.01` m, and no extra delivery-fraction tolerance. The complete approved
actions, limits, scenario multipliers and held seeds are in `tasks/*.json`.
These contracts are published for evaluation; held scenarios must not be
included in new model prompts.

## Evaluate another proposed design

For example save the following as `candidate.json`:

```json
{
  "pipe_upgrades": ["10", "11"],
  "pump_schedules": {"9": [1.0, 1.0, 1.0, 1.0]},
  "tank_control_shifts_m": {"2": 1.5}
}
```

Then run:

```sh
python run_demo.py --case Net1 --design candidate.json --output candidate_results.json
```

The custom-design path uses the same frozen sixteen-scenario contract, but
does not compare the new design to the original design's expected results.
No model is called. A validly executed candidate can be physically infeasible;
read `score.passed` and each scenario's checks. Frozen files should not be
edited to try a new design. Both cases can be selected with `--case` for a
smaller replay.

This example does **not** automate adding a model backend. Any model may
produce a design with the specified schema, which can be scored through the
custom-design command. Repeating the original generation/review experiment
requires a separate, explicit model adapter and newly frozen request protocol.

## Extending to another network

A new network requires more than replacing an input filename: establish the
source and license, approve device IDs and operating ranges, specify eight
development/eight held scenarios and constraints, verify mapping of actions to
the network's controls, and check contract feasibility. A new network with a
new contract is a new experimental task; it is not a replay of these two cases.
The reusable function is `engineering.grade(task, design, scenarios)`. The
present CLI intentionally accepts only these two audited frozen contracts.

## Provenance, environment and limits

- Source batch: `engineering_design_v04_20261014`.
- Both cases use producer `gpt-5.4`, repetition `0`, method `tool_same`.
- `cases.json` is an allowlisted extraction of designs and scoring objects
  from `final_results.json`; source and extracted hashes are in the manifest.
- No original request logs, model free-text answers, credentials or API
  configuration are included.
- `requirements.txt` pins the main numerical packages. The additional
  `requirements-lock-windows-py312.txt` records the full resolved application
  dependencies installed in the new validation environment.
- `recorded_environment.json` records the actual runtime versions. The
  example was checked in the existing research environment, then packaged,
  extracted to another directory and rerun with the same interpreter.
- A new virtual environment was subsequently created with
  `include-system-site-packages = false`. Installing `requirements.txt`
  succeeded using public-package wheels from pip's cache; `pip check` found
  no broken requirements. All 64 scenario evaluations matched the frozen
  references, and actual scores were exactly equal to the first replay.
  NumPy, pandapower and WNTR were verified to import from the new environment.
- This is a fresh dependency installation on the same Windows machine and
  base Python runtime. Another machine/OS, independent physical solver
  validation and field validity remain unverified. See `validation_report.json`.
- OpenTrust-authored example code (`run_demo.py` and `engineering.py`) is
  released under the included MIT `LICENSE`, with author authorization.
  Third-party network inputs and dependencies keep their original terms;
  see `THIRD_PARTY_NOTICES.md`. This does not relicense the paper or records.

The intended public location is
`https://github.com/Sumimi24/opentrust-research/tree/main/examples/engineering-replay`.
Refer to the actual repository revision for publication status and versioning.

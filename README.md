# OpenTrust: executable evidence for model analysis and RTL repair

Research report and reproducible artifacts. This repository does not claim an accepted publication, universal model advantage, a 95% deployment certificate, formal hardware correctness, or PPA results.

The website is in `docs/` and is intended for GitHub Pages. It presents a single research line: **explicit contracts → model analysis/generation → review/development feedback → independent executable truth → measured adoption quality**. Related literature and earlier work remain visible.

## New experiments

* Synthetic bounded protocols: transaction commit, resource leases, request/acknowledgment. 120 independently seeded specifications, 240 traces, four producer interfaces, three reviewer interfaces, plus blind independent analysis. 30 specifications are calibration only; 90 are test only. The full planned matrix contains 4,560 model calls.
* Open-source RTL integration repair: DMA writer, UDP receive guard, instruction-cache controller. Three pinned core projects; 18 functionally qualified injected wrapper faults; 72 initial repairs and same/cross-family paired continuation routes, each capped at three total model calls.

These are separate studies. Protocol analysis accuracy is not RTL correctness, and injected wrapper faults are not historical upstream bugs. Cases, API calls, seed replays, and independent projects must not be used interchangeably as sample counts.

## Offline reproduction

Use Python 3 with the standard library:

```text
python reproduce_protocol.py
```

The script rechecks all 240 truths with two CPU implementations, verifies the 960 saved candidate labels, and reruns the frozen calibration-only route analysis and specification-cluster bootstrap. It does **not** call models or repeat RTL simulations. API metadata in `research/protocol_formal/api_attempts_metadata.jsonl` omits repeated request payloads; the full original records and frozen sources are retained in the downloadable `docs/assets/protocol-study.zip`.

To preview the site:

```text
python -m http.server 8766 --directory docs
```

Open `http://127.0.0.1:8766/`.

## Execution and corrections

Experimental API credentials were loaded privately in memory and are not published. The published model labels come from the gateway's response; vendor identity has not been independently authenticated. All unsuccessful requests count in actual calls; truncated or malformed producer answers fail, malformed reviewer answers reject and are counted separately.

One transport-error response lacked a `text` field and interrupted input assembly. Execution resumed using an empty proposal for that existing failed call, without retrying it or changing successful outputs. The original runner and execution revision record remain in the archive. A broader-domain CPU check later corrected handling of negative initial timestamps and negative deadlines; **all 240 actual task labels were unchanged**, verified against both frozen and corrected implementations.

The RTL environment used Linux CPU simulation, Python 3.10, cocotb 1.9.2, Icarus 12 and Verilator 5.032. Compilation adaptations for the owner's OSS filesystem are environment-specific. Original scores/logs support the reported execution; offline result replay should not be called a fresh hardware simulation. No GPU was used or controlled.

## Sources and licenses

Pinned upstream projects: [verilog-axi](https://github.com/alexforencich/verilog-axi/tree/516bd5dadc3365b7f9e225d2af8fe0b8d804fe53), [verilog-ethernet](https://github.com/alexforencich/verilog-ethernet/tree/77320a9471d19c7dd383914bc049e02d9f4f1ffb), [Ibex](https://github.com/lowRISC/ibex/tree/af456e25575013668ab56725268126f6b0feca35). Their original licenses apply: MIT for the first two and Apache-2.0 for Ibex. The first two repositories are superseded by Taxi; historical versions are retained for reproducibility.

Evaluation design references: [Learn then Test](https://arxiv.org/abs/2110.01052), [VerilogEval](https://github.com/NVlabs/verilog-eval), [RTLLM](https://github.com/hkust-zhiyao/RTLLM), [RTL-Repair](https://github.com/ekiwi/rtl-repair), [SWE-bench](https://www.swebench.com/original.html), [CVDP](https://github.com/NVlabs/cvdp_benchmark). Website structure references: [Nerfies](https://nerfies.github.io/), [Diffusion Policy](https://diffusion-policy.cs.columbia.edu/), [SWE-bench](https://www.swebench.com/). The website is independently implemented; no template code or third-party visual assets were copied.

See the website's artifacts section for the actual completion audit, data and report. Unfinished experimental stages are labeled explicitly until their audit passes.

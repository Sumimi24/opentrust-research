# 大语言模型辅助工程设计中的执行反馈与审查——配电与供水网络的对照研究

<!-- CURRENT_ENGINEERING_RELEASE -->
2026-10-15 修订。本文通过 API 调用现有大语言模型开展配电与供水设备控制设计的同起点对照研究。
模型负责生成、选测、审查与修订，工程仿真负责动作执行与评分。现有仓库名称仅为材料托管标识，不是本文的方法或框架名称。
主论文及参考文献共 5 页，必要附录单独提供；新增双域最小 CPU 重放示例。
本次更新没有重新调用模型，也没有增加模型性能样本。

- [研究主页与下载](https://sumimi24.github.io/opentrust-research/)
- [精简论文](docs/materials/ai4e-paper.pdf) · [附录](docs/materials/ai4e-supplement.pdf) · [完整稿](docs/materials/ai4e-paper-with-appendix.pdf)
- [论文 LaTeX 源码及分析](docs/materials/ai4e-source.zip)
- [海报 PDF](docs/materials/ai4e-poster.pdf) · [可编辑 PPTX](docs/materials/ai4e-poster.pptx)
- [最小 CPU 示例源码](examples/engineering-replay/) · [示例 ZIP](docs/materials/engineering-replay.zip)

## 已完成的研究与证据

16 个筛选后网络（13 配电、3 供水），3 种声明配置各重复 2 次，形成 96 个共同起点和 672 条相关路线。
候选反馈使完整合同合格数由同配置的 46/96 增至 64/96，跨配置的 44/96 增至 65/96；收益主要来自配电。
8 个保留工况全部通过的数量分别为 51→68、46→70。完整审查与屏蔽完整审查均为 64/96，不能据此证明审查等效或普遍无效。
旧供水独立批次有 6/24 条标签因动作语义复评改变，不能并入当前 96 个起点。
CPU 参照的预算和结构重置权限不同，当前结果不证明完整模型流程优于工程优化。

## 不调用模型的物理重放

使用 Python 3.12：

```sh
cd examples/engineering-replay
python -m pip install -r requirements.txt
python run_demo.py
```

示例包含一个 Kerber 配电网和一个 Net1 供水网、合同、两组初始与最终方案。
4 份记录各运行 16 个工况，共 64 次场景评估；配电两阶段方案相同。
标签、逐项检查和数值测量均与冻结记录匹配。已验证原环境、异目录解压，以及同一 Windows 机器上禁用系统包的新建虚拟环境安装和重放。
该验证不涉及新模型调用、另一台机器、跨操作系统或独立物理求解器。

可用 `--case Net1 --design candidate.json` 评分自己的方案，输入格式见示例 README。
新增网络仍需定义批准动作、工况、物理约束与资格检查；示例不是任意模型/网络的自动接入平台。

## 许可和研究边界

新增示例代码采用其目录中的 MIT 许可。第三方网络、依赖、论文和实验记录不因该许可而被重新授权，详见示例 `THIRD_PARTY_NOTICES.md`。
没有发布私人交接手册、访问凭据或完整私有请求日志。
公开保留工况供复核使用，新的最终评估应建立独立条件。论文、网站与模型名称均不表示已录用、后端权重已认证或获得现场安全保证。

## 历史研究

以下保留先前协议与 RTL 研究说明，其样本与结果独立于当前工程设计研究。

<!-- HISTORICAL_RESEARCH -->
### Earlier protocol and RTL studies

Research report and reproducible artifacts. This repository does not claim an accepted publication, universal model advantage, a 95% deployment certificate, formal hardware correctness, or PPA results.

The earlier protocol and RTL studies are preserved in `docs/historical-protocol-rtl.html`. Their tasks, validation procedures and results are separate from the current power and water design study.

## New experiments

* Synthetic bounded protocols: transaction commit, resource leases, request/acknowledgment. 120 independently seeded scenarios covering 51 unique parameter configurations, 240 distinct traces, four producer interfaces, three reviewer interfaces, plus blind independent analysis. 30 scenarios are calibration only; 90 are test only. Parameter values overlap the splits; this evaluates fresh seeded traces within the protocol families, not unseen-parameter generalization. The completed formal matrix contains 4,560 actual model calls, including three transport failures.
* Open-source RTL integration repair: DMA writer, UDP receive guard, instruction-cache controller. Three pinned core projects; 18 functionally qualified injected wrapper faults; 72 initial repairs and same/cross-family paired continuation routes, each capped at three total model calls.

The RTL study completed 272 actual API calls and 216 route records. After execution-only reassessment with frozen original decisions and the necessary source check, correct adoption was 19/72 (one call), 24/72 (same family) and 27/72 (cross family). The descriptive fault-cluster interval for cross minus same crosses zero. A separate source-gated pipeline smoke completed 25 calls and 12 cases, with 8 correct adoptions and no observed false adoption. These are finite simulation results, not deployment risk certificates.

These are separate studies. Protocol analysis accuracy is not RTL correctness, and injected wrapper faults are not historical upstream bugs. Cases, API calls, seed replays, and independent projects must not be used interchangeably as sample counts.

Each of the 720 blind analyses is reused for comparison with the four producer proposals on the same trace. The website's one/three-review budget describes a hypothetical route for a single proposal, not the actual cost of collecting the full matrix. Equal API-call counts do not imply equal token or monetary costs. Component token totals and parameter-overlap diagnostics are available in `research/protocol_formal/dataset_scope_audit.json`.

## Offline reproduction

Use Python 3 with the standard library:

```text
python reproduce_protocol.py
python reproduce_rtl_results.py
```

The first script rechecks all 240 truths with two CPU implementations, verifies the 960 saved candidate labels, and reruns the frozen calibration-only route analysis and specification-cluster bootstrap. It does **not** call models or repeat RTL simulations. API metadata in `research/protocol_formal/api_attempts_metadata.jsonl` omits repeated request payloads; the full original records and frozen sources are retained in the downloadable `docs/assets/protocol-study.zip`.

To preview the site:

```text
python -m http.server 8766 --directory docs
```

Open `http://127.0.0.1:8766/`.

## Execution and corrections

Experimental API credentials were loaded privately in memory and are not published. The published model labels come from the gateway's response; vendor identity has not been independently authenticated. All unsuccessful requests count in actual calls; truncated or malformed producer answers fail, malformed reviewer answers reject and are counted separately.

One transport-error response lacked a `text` field and interrupted input assembly. Execution resumed using an empty proposal for that existing failed call, without retrying it or changing successful outputs. The original runner and execution revision record remain in the archive. A broader-domain CPU check later corrected handling of negative initial timestamps and negative deadlines; **all 240 actual task labels were unchanged**, verified against both frozen and corrected implementations.

The RTL environment used Linux CPU simulation, Python 3.10, cocotb 1.9.2, Icarus 12 and Verilator 5.032. Compilation adaptations for the owner's OSS filesystem are environment-specific. Original scores/logs support the reported execution; offline result replay should not be called a fresh hardware simulation. No GPU was used or controlled.

The second reproduction command requires the completed RTL archive in `docs/assets/rtl-repair-study.zip`. It checks the 216 saved route rows, source identities, selection before independent testing, seed sets, qualification records and actual call accounting. It also rechecks the source-contract audit, all 216 execution-corrected rows with frozen original acceptance decisions, and the separate 12-case source-gated smoke including its source omissions and call cap. It does not compile or simulate hardware. The archive also retains the pinned upstream archives, frozen contracts, wrapper sources, test code and compiler adaptations. Experimental runners retain their original machine-specific paths for provenance; rerunning API or RTL execution requires configuring those paths and installing the listed CPU tools. No credentials are included.

## Sources and licenses

Pinned upstream projects: [verilog-axi](https://github.com/alexforencich/verilog-axi/tree/516bd5dadc3365b7f9e225d2af8fe0b8d804fe53), [verilog-ethernet](https://github.com/alexforencich/verilog-ethernet/tree/77320a9471d19c7dd383914bc049e02d9f4f1ffb), [Ibex](https://github.com/lowRISC/ibex/tree/af456e25575013668ab56725268126f6b0feca35). Their original licenses apply: MIT for the first two and Apache-2.0 for Ibex. The first two repositories are superseded by Taxi; historical versions are retained for reproducibility.

Evaluation design references: [Learn then Test](https://arxiv.org/abs/2110.01052), [VerilogEval](https://github.com/NVlabs/verilog-eval), [RTLLM](https://github.com/hkust-zhiyao/RTLLM), [RTL-Repair](https://github.com/ekiwi/rtl-repair), [SWE-bench](https://www.swebench.com/original.html), [CVDP](https://github.com/NVlabs/cvdp_benchmark). Website structure references: [Nerfies](https://nerfies.github.io/), [Diffusion Policy](https://diffusion-policy.cs.columbia.edu/), [SWE-bench](https://www.swebench.com/). The website is independently implemented; no template code or third-party visual assets were copied.

See the website's artifacts section for the actual completion audit, data and report. Unfinished experimental stages are labeled explicitly until their audit passes.

## RTL source and execution audit

The original repair instruction required integrating the supplied immutable core and returning only the requested wrapper. The original simulation guard did not enforce core presence. The original independent cache run also encountered OSS generated-file overwrite failures after identical source uploads reset file modification times; those execution failures are not valid evidence of functional defects. A separate posthoc `source_contract_audit.json` checks this necessary source obligation, preserving original functional scores and decisions. Missing core instances cannot count as contract-correct adoption even if the behavior tests pass. An instance being present is a necessary check, not proof that every output depends on the core. The website distinguishes these counts.

A separate `precision_revision/` reassesses all frozen final sources after supplying the simulator default `1ns/1ps`, prohibiting reuse of old compiled binaries, and preserving immutable, byte-verified source files so independent scoring does not trigger an unnecessary rebuild. It requalifies the references and injected faults, repeats development and independent seeds, and makes zero model calls. Original acceptance decisions remain frozen. The amendment does not undo failures already supplied to models as feedback; route comparisons retain this limitation. Standalone replacement modules do not become valid integrations merely because this execution correction lets them run.

Optional scientific figure export requires matplotlib: `python plot_results.py`. The website also offers the resulting SVG files directly.

The separate 12-case source-gated smoke retains the original broken integration context at each repair call, uses new development and independent seeds, and checks core omissions before simulation. It is a pipeline readiness check, not a comparison of method gains against the earlier run. Runtime credential loaders remain local; a fresh API execution also needs a configured adapter. The public standard-library reproduction commands validate saved evidence and do not pretend to rerun model calls.

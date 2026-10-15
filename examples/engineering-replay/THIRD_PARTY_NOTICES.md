# Source and dependency notices

This example does not redistribute installed Python packages or solver
binaries. Install them using their own distributions, which retain their
licenses and bundled-component notices. The two included network inputs have
the following provenance:

* `inputs/kerber_overhead_prepared.json`: derived in the original study from
  pandapower's `create_kerber_landnetz_freileitung_1` network. pandapower 3.5.6
  is distributed under BSD-3-Clause; the installed distribution's unmodified
  license and author list are included as `licenses/pandapower-LICENSE` and
  `licenses/pandapower-AUTHORS`. Network documentation:
  https://pandapower.readthedocs.io/en/stable/networks/kerber.html . This is
  an example model, not operational utility network data.
* `inputs/Net1.inp`: the EPANET Example Network 1 distributed with WNTR's
  network library, byte-identical to the frozen study input. WNTR 1.5.0 is
  distributed under the Revised BSD license and includes third-party notices;
  the installed distribution's complete notice is retained as
  `licenses/wntr-LICENSE.md`. Library source:
  https://usepa.github.io/WNTR/libraries.html . The input file itself has no
  additional standalone license text; its title identifies it as the EPANET
  example network. This notice reports its distribution provenance rather
  than assigning a new license to upstream material.

`source_manifest.json` records the source study paths and SHA-256 hashes for
the code, contracts and inputs, and identifies the design/score extraction.
The upstream network conditions are retained in the task context; experiment
changes are applied by the included frozen implementation.

The directly imported third-party packages are NumPy, pandapower and WNTR.
They depend on other packages such as SciPy, pandas, NetworkX and Matplotlib.
Those packages and bundled solver libraries keep their respective licenses;
this example does not replace or relicense those distributions. The local
license copies above were read from installed distribution metadata, not
inferred from package names.

With author authorization, the OpenTrust-authored example code `run_demo.py`
and `engineering.py` is available under the MIT license included as `LICENSE`.
This grant does not cover or relicense the third-party `inputs/`, dependency
packages, their notices, or upstream-derived task data. It does not grant a
new license for the paper or experimental records. All upstream rights and
notices remain applicable.

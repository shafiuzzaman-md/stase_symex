# STASE
STASE (STatic Analysis guided Symbolic Execution) is a two-phase analysis framework designed to detect and confirm emergent operations/ weird instructions. Each phase can be run independently or together in sequence.

**Phase 1:  Rule-based Static Analysis (STASE_RbSA):** This phase identifies vulnerabilities using rule-based static analysis.

| Artifact   | Description                                         |
| ---------- | --------------------------------------------------- |
| **Input**  | Source code |
| **Output** | Vulnerability reports in .csv and .json|

**Phase 2:  Guided Symbolic Execution (STASE_SYMEX):** Using the results of STASE_RbSA, this phase generates and runs KLEE-based symbolic execution harnesses to confirm whether vulnerabilities are real and extract precise path constraints (preconditions and postconditions).

| Artifact   | Description                                         |
| ---------- | --------------------------------------------------- |
| **Input**  | Source code, Static analysis output, (Optional) Driver stubs |
| **Output** | Vulnerability reports in .txt and .json|



# STASE Symbolic Execution Workflow (STASE_SYMEX)
STASE_SYMEX combines static-analysis results with KLEE-based symbolic execution to confirm vulnerabilities and extract path constraints that trigger them.
```
🟩 REQUIRED INPUTS                                 🔧 PROCESS: STASE_SYMEX Engine                                 📤 OUTPUTS
┌────────────────────┐                  ┌──────────────────────────────────────────────────────────┐     ┌────────────────────────────┐
│   Source Code      │                  │  setup_environment.py                                    │     │ Human-readable Report      │
│ (UEFI / Kernel)    ├────┬────────────▶│                                                          ├────▶│ stase_output/*.txt         │
└────────────────────┘    │             │  setup_driver.py                                         │     │ (Pre/Post conditions)      │
                          │             │  ├─ Generates KLEE driver with symbolic inputs           │     └────────────────────────────┘
┌────────────────────────────┐          │  ├─ Inserts klee_assert at specified vulnerability lines │
│ Static Analysis Output     ├────┐     │  └─ Includes symbolic/concrete vars, memory models       │     ┌────────────────────────────┐
│ (entry, vuln, line, etc.)  │    └────▶│                                                          ├────▶│ Machine-readable Report    │
└────────────────────────────┘          │  (Optional) Manual stub insertion into the driver        │     │ formatted_output/*.json    │
 🟨 OPTIONAL INPUTS                     │                                                          │     │ (type, file, line, vars...)│
┌──────────────────────────┐            │  run_analysis.py                                         │     └────────────────────────────┘
│ Hand-edited Driver Stubs │───────────▶│  └── Invokes KLEE for symbolic execution                 │
│ • Unresolved symbols     │            └──────────────────────────────────────────────────────────┘
│ • Uninteresting functions│
│ • Concretization logic   │
└──────────────────────────┘


```
---


###  Input

| Artifact                     |Description                                                            |
|------------------------------|-----------------------------------------------------------------------|
|  Source code                 | EDK2 / Linux source tree                                                 |
| Static-analysis result       | Entrypoint, attacker-controlled variables, vulnerability type, vulnerability location|
| (Optional) Hand-edited driver stubs (under `inputs/`)| KLEE drivers are generated from static analysis results via `setup_driver.py`; contains entrypoint call, symbolic variables, and stubs, then hand-edited for any extra stubs |
---

## Output
- After run_analysis.py finishes you will find a KLEE output folder (e.g. stase_generated/klee-out-0/).
- STASE_SYMEX post‑processes this folder and writes two parallel reports that describe every assertion that KLEE managed to violate.
  
| Report name               | Type / format | Description      |
| ------------------------- | ------------- | -------------------------------------------------------------------------- |
| **`stase_output/*.txt`** | Human‑readable pre‑/post‑condition | Precondition + postcondition for each violated assertion  |
| **`formatted_output/*.json`**   | JSON | Machine-parseable bug report (type, file, line, variables, assertion, precondition|

---
## Step 0: Install KLEE Symbolic Execution Engine 
STASE uses KLEE as the underlying symbolic execution engine. Follow [these steps](install_klee.md) to install KLEE.

## **1. Setup (One Time Only)**

Run **once** to set up the environment and prepare environment-wide stubs and includes.

```
python3 setup_environment.py <source-code-location> <clang-path> <klee-path>
```
Example on EDK II:
```
python3 setup_edk2_environment.py ../eval2_edk2-main /usr/lib/llvm-14/bin/clang /home/shafi/klee_build/bin/klee
```

## **2. For Each Vulnerability**
### **2.1 Generate Driver and Insert Assertion**
#### 2.1  Quick reference
Run once for each vulnerability detected by static analysis to generate a KLEE driver and insert assertion.
```
python3 setup_driver.py \
  --entry-src   <path/to/entrypoint.c>     \
  --entry-func  <EntryPointSymbol>         \
  --vuln        <OOB_WRITE|WWW|CFH>        \
  --assert-line <N>                        \
  --target-src  <same/or/other/file.c>     \
  --assertion   "<expr inside klee_assert>"\
  --symbolic    "type name"   [...]        \
  --concrete    "stmt;"       [...]        \
  --global/-g   "type name"   [...]        \
  --malloc      "ptr size"    [...]        \
  --default-malloc <size|0>
```
- `--symbolic` Declares and makes variables symbolic
- `--concrete` Adds explicit initialization (malloc, assume, etc.)
- `--malloc` Pre-allocates symbolic buffer for double pointers
- `--default-malloc` his option tells the system to automatically allocate a buffer of size N bytes for any double pointer (like CHAR8 **OutputBuffer) that hasn’t been manually allocated using --malloc.
- `--global/-g` globals (visible to instrumented source).

Outputs:

- inputs/klee_driver___.c
- Instrumented source with assertion


#### 2.2  Example: Iconv OOB_WRITE
```
python3 setup_driver.py \
  --entry-src   Testcases/Sample2Tests/CharConverter/CharConverter.c \
  --entry-func  Iconv \
  --vuln        OOB_WRITE \
  --assert-line 146 \
  --target-src  Testcases/Sample2Tests/CharConverter/CharConverter.c \
  -g           "unsigned OutputBuffer_cap" \
  --symbolic   "ICONV_T *CharDesc" \
  --symbolic   "CHAR8 *InputBuffer" \
  --malloc     InputBuffer 4096 \
  --symbolic   "INTN InputSize" \
  --symbolic   "CHAR8 **OutputBuffer" \
  --symbolic   "INTN *OutputSize" \
  --symbolic   "unsigned OutputBuffer_cap" \
  --concrete   "*OutputBuffer = malloc(OutputBuffer_cap);" \
  --assertion  "OutIndex < OutputBuffer_cap"
```
This harness:
- `OutputBuffer_cap` (symbolic + global): Models the buffer size.
- `*OutputBuffer = malloc(OutputBuffer_cap)`;: Allocates a concrete buffer of symbolic size.
- `--malloc InputBuffer 4096`: Ensures the input read (e.g., InputBuffer[i+1]) stays in bounds.
- Asserts write bound to prevent OOB at `(*OutputBuffer)[OutIndex++]`

Results:
```
inputs/klee_driver_Iconv_OOB_WRITE_146.c
stase_generated/instrumented_source/.../CharConverter.c   (now contains klee_assert)
```

### Step 3: Run Analysis

Once the driver and assertion are ready:

#### Single Driver
```
python3 run_analysis.py <driver.c> [<max_klee_time_seconds>]

```

Example:
```
python3 run_analysis.py ../inputs/klee_driver_Iconv_OOB_WRITE_146.c 
```

####  Batch Mode (all drivers under inputs/)
```
python3 run_analysis.py --batch

```
Output appears under `stase_generated/klee-out-*`

#### Output:
``` cd .. ```
- `stase_output/*.txt`
- `formatted_output/*.json`

Example JSON Output
```
{
  "type": "OOB_WRITE",
  "file": "Testcases/Sample2Tests/CharConverter/CharConverter.c",
  "line": 146,
  "variables": ["OutputBuffer_cap", "InputBuffer", "InputSize"],
  "assertion": "OutIndex < OutputBuffer_cap",
  "precondition": "..."
}
```

### Step 4: Human-in-the-loop edits (if needed)
Symbolic execution may not always succeed without minor guidance. Use the table below to adjust and re‑run Step 3  (run_analysis.py) when needed:

| Scenario                                                  | Action| 
|-----------------------------------------------------------|------ |
|KLEE: ERROR – `undefined reference`| Add stubs for missing external or platform-specific functions.|
|KLEE finishes instantly  | Loosen constraints: widen assumptions, add more symbolic inputs.|
|KLEE runs indefinitely | Likely due to path explosion. Stub out irrelevant functions, Harden constraints: narrow assumptions, limit malloc sizes |

##  Project Layout
```
project_root/
├── stase_symex/
│   ├── setup_environment.py
│   ├── setup_driver.py
│   ├── run_analysis.py
│   └── (other helper scripts)
├── stase_generated/
│   ├── instrumented_source/            # Copied + instrumented source tree
│   ├── generated_klee_drivers/
│   ├── global_stubs.h
│   ├── global_stub_defs.c
│   ├── driver_stubs.c
│   └── settings.py
├── inputs/
│   └── klee_driver_<...>.c             # User-prepared drivers
├── stase_output/
│   └── klee_driver_<...>_output.txt  
├── formatted_output/
│   └── klee_driver_<...>_output.json  
└── (user's original source code placed anywhere)

```

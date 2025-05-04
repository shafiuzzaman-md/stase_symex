# STASE Symbolic Execution Workflow (STASE_SYMEX)
STASE_SYMEX combines static-analysis results with KLEE-based symbolic execution to confirm vulnerabilities and extract path constraints that trigger them.

---

## Input

| Item                         | Notes                                                                 |
|------------------------------|-----------------------------------------------------------------------|
| Source tree                  | Any UEFI / kernel-module code base                                    |
| Vulnerability type           | `OOB_WRITE`, `WWW` (write-what-where) or `CFH` (control-flow hijack)  |
| Assertion location           | Line number of the vulnerable instruction (in `--target-src`)         |
| Driver `.c` (under `inputs/`)| Generated via `setup_driver.py`; contains entrypoint call, symbolic variables, and stubs, then hand-edited for any extra stubs |

---

## Output
- After run_analysis.py finishes you will find a KLEE output folder (e.g. stase_generated/klee-out-0/).
- STASE_SYMEX post‑processes this folder and writes two parallel reports that describe every assertion that KLEE managed to violate.
  
| Report name               | Type / format | Description      |
| ------------------------- | ------------- | -------------------------------------------------------------------------- |
| **`stase_output/*.txt`** | Human‑readable pre‑/post‑condition | Precondition + postcondition for each violated assertion  |
| **`formatted_output/*.json`**   | JSON | Machine-parseable bug report (type, file, line, symbolic variables)|

---

## Step 1: Setup Environment

Run **once** to set up the environment and prepare environment-wide stubs and includes.

```
python3 setup_environment.py <source-code-location> <clang-path> <klee-path>
```
Example on EDK II:
```
python3 setup_edk2_environment.py ../edk2-testcases-main /usr/lib/llvm-14/bin/clang /home/shafi/klee_build/bin/klee
```

## Step 2: Setup Driver and Instrument code
### 2.1  Quick reference
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
- `--default-malloc` Fallback size for unallocated double pointers


### 2.2  Example: Iconv OOB_WRITE
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

## Step 3: Run Analysis

Once the driver and assertion are ready:

### Single Driver
```
python3 run_analysis.py <driver.c> [<max_klee_time_seconds>]

```

Example:
```
python3 run_analysis.py ../inputs/klee_driver_Iconv_OOB_WRITE_146.c 
```

###  Batch Mode (all drivers under inputs/)
```
python3 run_analysis.py --batch

```
Output appears under `stase_generated/klee-out-*`

## Step 4: Human-in-the-loop edits (if needed)
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
└── (user's original source code placed anywhere)

```

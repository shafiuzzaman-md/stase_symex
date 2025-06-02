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
# KLEE Symbolic Execution Engine Installation
STASE uses KLEE as the underlying symbolic execution engine. Follow [these steps](install_klee.md) to install KLEE.

# Static Analysis Integration

The static analysis output contains JSON files. Each JSON represents a potential vulnerability.

## Mapping Static Analysis Fields to `setup_driver.py` Inputs
| JSON Field       | `setup_driver.py` Argument       | Description                             |
|------------------|----------------------------------|-----------------------------------------|
| `Taint Source`   | `--entry-src`, `--entry-func`    | Entry function and its source file      |
| `Taint Sink`     | `--target-src`                   | File where assertion should be inserted |
| `Source`         | `--symbolic`                     | Tainted variable to make symbolic       |
| `Destination`    | `--assertion`                    | Used in klee_assert expression          |
| `Program Location` | `--assert-line`                | Line number for assertion insertion     |


# STASE SYMEX: UEFI Firmware Workflow

## **1. Environment Setup (One Time Only)**

Run **once** to set up the environment and prepare environment-wide stubs and includes.

```
python3 setup_edk2_environment.py <source-code-location>
```
Example:
```
# from stase_symex/
python3 setup_edk2_environment.py ../edk2-testcases-main 
```

## **2. Driver and Instrumentation (For Each Vulnerability)**
- Use instrument.py to inject assertions, comment irrelevant code, and stub functions in the target source.
- Use setup_driver.py to generate a standalone KLEE driver.

### Instrument Source Code
```
python3 instrument.py \
  --target-src <relative/path/to/source.c> \
  --assert-line <line-number> \
  --assertion "<klee_assert_expr>" \
  [--comment-lines <L1> <L2> ...] \
  [--stub-functions <func1> <func2> ...]
```
Outputs: Instrumented source with assertion

Example:
```
python3 instrument.py \
  --target-src Testcases/Sample2Tests/CharConverter/CharConverter.c \
  --assert-line 146 \
  --assertion "OutIndex < OutputBuffer_cap" \
  --stub-functions AsciiStrCmp

```
Outputs:
```
stase_generated/instrumented_source/.../CharConverter.c   (now contains klee_assert)
```

### Generate KLEE Driver
`setup_driver.py` Usage:

Mandatory Flags
```bash
--entry-src    <rel-path>     # Source file containing entry point
--entry-func   <symbol>       # Entry function name (e.g., Iconv)
--vuln         <OOB_WRITE|WWW|CFH>
--assert-line  <line-number>  # Insert assertion before this line
--target-src   <rel-path>     # File where vulnerability lies
--assertion    "<expr>"       # klee_assert expression
```
Optional Flags
```bash
--symbolic      "type name"       # Symbolic variable in main()
--concrete      "stmt;"           # Concrete init code inside main()
--global        "type name"       # File-scope globals before main()
--malloc        PTR SZ            # Allocate buffer for T** manually
--default-malloc <size|0>         # Default size for T** allocations
```


Outputs: inputs/klee_driver___.c

Example:
```
python3 setup_driver.py \
  --entry-src   Testcases/Sample2Tests/CharConverter/CharConverter.c \
  --entry-func  Iconv \
  --vuln        OOB_WRITE \
  --assert-line 146 \
  --target-src  Testcases/Sample2Tests/CharConverter/CharConverter.c \
  --global           "unsigned OutputBuffer_cap" \
  --symbolic   "ICONV_T *CharDesc" \
  --symbolic   "CHAR8 *InputBuffer" \
  --malloc     InputBuffer 4096 \
  --symbolic   "INTN InputSize" \
  --symbolic   "CHAR8 **OutputBuffer" \
  --symbolic   "INTN *OutputSize" \
  --symbolic   "unsigned OutputBuffer_cap" \
  --concrete   "*OutputBuffer = malloc(OutputBuffer_cap);"
```
Outputs:
```
inputs/klee_driver_Iconv_OOB_WRITE_146.c
```


This harness:
- `OutputBuffer_cap` (symbolic + global): Models the buffer size.
- `*OutputBuffer = malloc(OutputBuffer_cap)`;: Allocates a concrete buffer of symbolic size.
- `--malloc InputBuffer 4096`: Ensures the input read (e.g., InputBuffer[i+1]) stays in bounds.
- Asserts write bound to prevent OOB at `(*OutputBuffer)[OutIndex++]`

## **3. Run Analysis**

Once the driver and assertion are ready:

### Single Driver
```
python3 run_analysis.py <driver.c> --clang-path <clang> --klee-path <klee> [--timeout <max_klee_time_seconds>]
```

Example:
```
python3 run_analysis.py ../inputs/klee_driver_Iconv_OOB_WRITE_146.c  --clang-path /usr/lib/llvm-14/bin/clang   --klee-path /home/shafi/klee_build/bin/klee
```

###  Batch Mode (all drivers under inputs/)
```
python3 run_analysis.py --batch --clang-path <clang> --klee-path <klee> [--timeout <max_klee_time_seconds>]
```
Output appears under `stase_generated/klee-out-*`

### Output:
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

## **4. Human-in-the-loop edits (if needed)**
Symbolic execution may not always succeed without minor guidance. Use the table below to adjust and re‑run Step 3  (run_analysis.py) when needed:

| Scenario                                                  | Action| 
|-----------------------------------------------------------|------ |
|KLEE: ERROR – `undefined reference`| Add stubs for missing external or platform-specific functions.|
|KLEE finishes instantly  | Loosen constraints: widen assumptions, add more symbolic inputs.|
|KLEE runs indefinitely | Likely due to path explosion. Stub out irrelevant functions, Harden constraints: narrow assumptions, limit malloc sizes |

# STASE SYMEX: Linux Kernel Workflow
## **1. Environment Setup (One Time Only)**
```
python3 setup_kernel_environment.py <kernel-src>
```
Example:
```
# from stase_symex/
python3 setup_kernel_environment.py  ../eval2_linux-main 
```
## **2. Driver and Instrumentation (For Each Vulnerability)**



### Instrument Source Code
```
python3 instrument_kernel.py \
  --target-src <relative/path/to/source.c> \         # C file where assertion will be inserted
  --assert-line <line-number> \                      # Line number to insert the assertion (before this line)
  --assertion "<klee_assert_expr>" \                 # The assertion to insert (must be a valid C statement)
  [--comment-lines <L1> <L2> ...] \                   # Optional: lines to comment out instead of deleting
  [--helper-files <file1.c> <file2.c> ...] \          # Optional: preserve these extra C files (e.g., entrypoint helpers)
  [--stub-functions <stubs.json>]                    # Optional: JSON file of stubbed function definitions

```
Output: A new workspace under ../stase_generated_<N>/ with:

    - An instrumented version of the kernel source in instrumented_source/,
    - Inserted assertion at the specified location,
    - Stubbed-out irrelevant .c files,
    - A generated driver_stubs.c file if --stub-functions is provided.

Example:
```
python3 instrument_kernel.py \
   --entry-src   drivers/kbmi_net/kbmi_net.c \
  --target-src drivers/kbmi_usb/kbmi_usb.c \
  --assert-line 79 \
  --assertion 'klee_assert(!is_executable((uint64_t)message_buffer));'
```
### Generate KLEE Driver
`setup_driver.py` Usage:

Mandatory Flags
```bash
--entry-src    <rel-path>     # Source file containing entry point
--entry-func   <symbol>       # Entry function name (e.g., Iconv)
--vuln         <OOB_WRITE|WWW|CFH>
--assert-line  <line-number>  # Insert assertion before this line
--target-src   <rel-path>     # File where vulnerability lies
--assertion    "<expr>"       # klee_assert expression
```
Optional Flags
```bash
--symbolic      "type name"       # Symbolic variable in main()
--concrete      "stmt;"           # Concrete init code inside main()
--global        "type name"       # File-scope globals before main()
--malloc        PTR SZ            # Allocate buffer for T** manually
--default-malloc <size|0>         # Default size for T** allocations
```

Outputs: inputs/klee_driver___.c

Example:
```
python3 setup_driver.py   --entry-src   drivers/kbmi_net/kbmi_net.c   --entry-func  kbmi_net_init   --vuln        STACK_EXECUTABLE   --assert-line 79   --target-src  drivers/kbmi_usb/kbmi_usb.c   --global      "#define NOTIFY_OK 0"   --global      "char message_buffer[1024]"   --symbolic    "char message_buffer[MESSAGE_SIZE]"
```

Outputs:
```
inputs/klee_driver_kbmi_net_init_STACK_EXECUTABLE_79.c
```


## **3. Run Analysis**

Once the driver and assertion are ready:

### Single Driver
```
python3 run_analysis.py <driver.c> --clang-path <clang> --klee-path <klee> [--timeout <max_klee_time_seconds>]
```

Example:
```
python3 run_analysis.py ../inputs/klee_driver_kbmi_net_init_STACK_EXECUTABLE_79.c  --clang-path /usr/lib/llvm-14/bin/clang   --klee-path /home/shafi/klee_build/bin/klee
```

###  Batch Mode (all drivers under inputs/)
```
python3 run_analysis.py --batch --clang-path <clang> --klee-path <klee> [--timeout <max_klee_time_seconds>]
```
Output appears under `stase_generated/klee-out-*`

### Output:
``` cd .. ```
- `stase_output/*.txt`
- `formatted_output/*.json`

## **4. Human-in-the-loop edits (if needed)**
Symbolic execution may not always succeed without minor guidance. Use the table below to adjust and re‑run Step 3  (run_analysis.py) when needed:

| Scenario                                                  | Action| 
|-----------------------------------------------------------|------ |
|KLEE: ERROR – `undefined reference`| Add stubs for missing external or platform-specific functions.|
|KLEE finishes instantly  | Loosen constraints: widen assumptions, add more symbolic inputs.|
|KLEE runs indefinitely | Likely due to path explosion. Stub out irrelevant functions, Harden constraints: narrow assumptions, limit malloc sizes |

# Adding a New Environment
To support a new environment:
1. Create `setup_<env>_environment.py` (e.g., `setup_android_environment.py`)
2. Use common helper functions:
   - `next_workspace()` to create new workspace
   - `write_settings_py()` / `write_settings_json()` to emit tool paths
   - `copy_source_tree()` to copy sources if needed
3. Stub missing headers using `emit_fake_libc()` pattern
4. Ensure `instrumented_source/` is populated or structured properly



#  Project Layout
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

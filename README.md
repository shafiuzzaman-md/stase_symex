# STASE Symbolic Execution Workflow (STASE_SYMEX)

This repository implements symbolic exution using **STASE** (Static Analysis guided Symbolic Execution) to discover vulnerabilities (with vulnerability signature).
---

## Input

- Source code directory (e.g., EDK2 clone or Linux module)
- Driver `.c` file under `inputs/`:
  - Contains:
    - Symbolic declarations
    - Stub setup
    - Entry point invocation
- Assertion expression (derived from vulnerability type, e.g., OOB_WRITE)
- Symbolic execution timeout (optional)
---

## Output


---

## Step 1: Setup Environment

Run **once** to set up the environment and prepare environment-wide stubs and includes.

```
python3 setup_environment.py <source-code-location> <clang-path> <klee-path>


```
Example:
```
python3 setup_edk2_environment.py ../edk2-testcases-main /usr/lib/llvm-14/bin/clang /home/shafi/klee_build/bin/klee
```
This script will:

- Copy the source tree into `stase_generated/instrumented_source/`

- Rewrite `#include <...>` to `#include "..."` with full relative paths

- Comment out all `STATIC_ASSERT()` macros

- Extract protocol GUIDs and global variables into:
  - `global_stubs.h` and `global_stub_defs.c`

- Generate static driver stubs in `driver_stubs.c`
- Create a settings.py containing paths to Clang, KLEE, and source

## Step 2: Setup Driver and Instrument code
Run once for each vulnerability detected by static analysis to generate a KLEE driver and insert assertion.
```
python3 setup_driver.py \
  <entrypoint_source_file_relative_path> \
  <entrypoint_name> \
  <vulnerability_type> \
  <assertion_line_number> \
  <target_source_file_relative_path> \
  [--symbolic "type1 name1" "type2 name2" ...] \
  [--concrete "full_declaration1" "full_declaration2" ...]

```
Example:
```
python3 setup_driver.py \
  Testcases/Sample2Tests/CharConverter/CharConverter.c \
  Iconv \
  OOB_WRITE \
  146 \
  Testcases/Sample2Tests/CharConverter/CharConverter.c \
  --symbolic "ICONV_T *CharDesc" "CHAR8 *InputBuffer" "INTN InputSize" "CHAR8 **OutputBuffer" "INTN *OutputSize"\
  --concrete ""

```
This script will:
- Insert the assertion at the specified line into the target source
- Generate a driver skeleton under `inputs/` named:
    ```
    klee_driver_<EntryPointName>_<VulnerabilityType>_<LineNumber>.c

    ```
    For example:
    ```
    inputs/klee_driver_CharConverter_OOB_WRITE_146.c
    ```

- Populate includes, `initialize_stubs()`, symbolic declarations, concrete inits, and entrypoint call

### After Driver Generation: Human in the loop
Update the generated driver if needed:

- Add function stubs (if needed) for the uninteresting functions

- Add initialization for system globals

## Step 3: Run Symbolic Analysis

Once the driver and assertion are ready:

```
python3 run_analysis.py <driver.c> [<max_klee_time_seconds>]

```

Example:
```
python3 run_analysis.py \
  ../inputs/klee_driver_Iconv_OOB_WRITE_146.c \
  10
```
This will:

- Compile the driver with stubs into LLVM bitcode

- Run KLEE with the specified (or default 5s) timeout.

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
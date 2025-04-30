# STASE Symbolic Execution Workflow

This repository implements symbolic exution using **STASE** (Static Analysis guided Symbolic Execution) to discover vulnerabilities (with vulnerability signature).
---

## Input

- Source code directory (e.g., EDK2 clone or Linux module)
- Driver.c file under inputs/:
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

- Copy the source tree into stase_generated/instrumented_source/

- Rewrite #include <...> to #include "..." with full relative paths

- Comment out all STATIC_ASSERT() macros

- Extract protocol GUIDs and global variables into:
  - global_stubs.h and global_stub_defs.c

- Generate static driver stubs in driver_stubs.c

- Create a settings.py containing paths to Clang, KLEE, and source

## Step 2: Setup Driver
Run once for each vulnerability to generate an initial driver template.
```
python3 setup_driver.py \
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
  Iconv \
  OOB_WRITE \
  146 \
  Testcases/Sample2Tests/CharConverter/CharConverter.c \
  --symbolic "uint8_t InnerBuf[4]" "uint32_t j" "uint32_t last" \
  --concrete "gSmst = NULL;" "buffer_size = 0x20;"

```
This script will:
- Create a driver skeleton under inputs/ named:
```
klee_driver_<EntryPointName>_<VulnerabilityType>_<LineNumber>.c

```
For example:
```
inputs/klee_driver_CharConverter_OOB_WRITE_146.c
```

Driver will contain:
- Symbolic declarations for attacker-controlled inputs
- Concrete initializations for stubs and system fields

- Insert the assertion at the specified line into the target source
- Pre-fill includes, `initialize_stubs()`, and entrypoint call

### After Driver Generation: Manual Steps
- Add any custom stub initialization if needed

## Step 3: Run Symbolic Analysis

Once the driver is ready and the target source is instrumented, run:

```
python3 staseplusplus/run_analysis.py \
  <driver.c> \
  <target_source_file_relative_to_source_dir> \
   [<max_klee_time_seconds>]

```
Note: The last argument <max_klee_time_seconds> is optional. If omitted, it will default to 5 seconds.

Example:
```
python3 run_symbolic_analysis.py \
  ../inputs/klee_driver_CharConverter_OOB_WRITE_146.c \
  10



```
What this does:

- Loads the driver.c file

- Compiles the driver together with stubs into LLVM bitcode

- Runs KLEE symbolic execution with the specified (or default) timeout.

##  Project Layout
```
project_root/
├── stase/
│   ├── setup_environment.py
│   ├── setup_driver.py
│   ├── run_analysis.py
│   ├── (other helper scripts)
├── stase_generated/
│   ├── instrumented_source/
│   │   ├── (copied + instrumented source tree)
│   ├── generated_klee_drivers/
│   │   ├── 
│   ├── global_stubs.h
│   ├── global_stub_defs.c
│   ├── driver_stubs.c
│   ├── settings.py
├── inputs/
│   ├── klee_driver_template.c   <-- (example driver)
│   ├── (user-prepared drivers here)
├── (user's original source code placed anywhere)

```
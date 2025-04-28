# STASE Symbolic Execution Workflow

This repository implements symbolic exution using **STASE** (Static Analysis guided Symbolic Execution) to discover vulnerabilities (with vulnerability signature) .

---

## Input

- Source code directory under inputs/source/
- Driver .c file under inputs/:
  - Symbolic declarations
  - Stub setup
  - Entry point invocation
- Assertion expression to inject (derived from vulnerability type, e.g., OOB_WRITE)
- Assertion line number in the target source file
- Symbolic execution timeout
---

## Output


---

## Phase 1: Environment Configuration Harnesses (ECH)

Run **once** to set up the environment and prepare environment-wide stubs and includes.

```
python3 setup_ech.py <source-directory> <clang-path> <klee-path>

```
Example:
```
python3 setup_ech.py ../edk2-testcases-main /usr/lib/llvm-14/bin/clang /home/shafi/klee_build/bin/klee
```
This script will:

- Copy the source tree into stase_generated/instrumented_source/

- Rewrite #include <...> to #include "..." with full relative paths

- Comment out all STATIC_ASSERT() macros

- Extract protocol GUIDs and global variables into:
  - global_stubs.h and global_stub_defs.c

- Generate static driver stubs in driver_stubs.c

- Create a settings.py containing paths to Clang, KLEE, and source

## Phase 2: Path Exploration Harnesses (PEH)
Run once per assertion  (guided by static analysis).

```
python3 run_analysis.py \
  <driver_template.c> \
  <target_source_file.c> \
  <assertion_line_number> \
  <assertion_expression> \
  <max_klee_time_seconds>

```

Example:
```
python3 run_analysis.py \
  inputs/klee_driver_CharConverter_OOB_WRITE.c \
  Testcases/Sample2Tests/CharConverter/CharConverter.c \
  146 \
  "klee_assert(j <= last);" \
  5


```
 Where::
- Inserts the assertion at the specified line in the target source file

- Loads the driver .c file

- Compiles the driver together with stubs into LLVM bitcode

- Runs KLEE symbolic execution for the specified timeout

##  Project Layout
```
your_project_root/
├── staseplusplus/
│   ├── run_analysis.py
│   ├── setup_ech.py
│   ├── (other scripts)
├── stase_generated/
│   ├── instrumented_source/
│   │   ├── Testcases/Sample2Tests/CharConverter/CharConverter_146_instrumented.c
│   ├── generated_klee_drivers/
│   │   ├── klee_driver_CharConverter_OOB_WRITE_assert.c
├── inputs/
│   ├── source/
│   │   ├── Testcases/Sample2Tests/CharConverter/CharConverter.c
│   ├── klee_driver_CharConverter_OOB_WRITE.c
```
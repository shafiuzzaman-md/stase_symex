# STASE Analysis Workflow

This repository implements a streamlined pipeline for symbolic vulnerability analysis using **STASE** (Static Analysis guided Symbolic Execution) over UEFI firmware modules.

---

## Input

- Source code directory under analysis (must be a clone of EDK2 or compatible testcases)
- Entry point and vulnerable instruction location: From static analysis
- Assertion template: Derived for vulnerability type (e.g., OOB_WRITE)

---

## Output


---

## Phase 1: Environment Configuration Harnesses (ECH)

Run **once** to set up the environment, prepare headers, and disable static assertions.

```
python3 setup_ech.py <edk2-directory> <clang-path> <klee-path>
```
Example:
```
python3 setup_ech.py ../edk2-testcases /usr/lib/llvm-14/bin/clang /home/shafi/klee/build/bin/klee
```
This script will:

- Rewrite all #include <...> to absolute #include "..." paths for compatibility

- Comment out all STATIC_ASSERT() statements

- Save configuration in settings.py

## Phase 2: Path Exploration Harnesses (PEH)
Run once per assertion (generated via static analysis)
```
python3 run_analysis.py \
  ../edk2-testcases/Testcases/Sample2Tests/CharConverter/CharConverter.c \
  107 \
  OOB_WRITE \
  "(*OutputBuffer)[i] = (CHAR16)InputBuffer[i];"
```
 What this does:
- Checks if the assertion is already inserted

- If not, auto-inserts it at the specified line

- Generates a per-assertion KLEE driver for the relevant entrypoint (e.g., CharConverterEntryPoint)

- Compiles the instrumented file to LLVM bitcode

- Runs KLEE symbolic execution to explore relevant paths and check satisfiability of the assertion
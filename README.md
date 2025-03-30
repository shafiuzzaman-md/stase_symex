# STASE Symbolic Execution Workflow

This repository implements symbolic exution using **STASE** (Static Analysis guided Symbolic Execution) to discover vulnerabilities (with vulnerability signature) in UEFI modules.

---

## Input

- Source code directory under analysis (must be a clone of EDK2)
- Entry point and vulnerable instruction location: From static analysis
- Assertion template: Derived for vulnerability type (e.g., OOB_WRITE)

---

## Output


---

## Phase 1: Environment Configuration Harnesses (ECH)

Run **once** to set up the environment.

```
python3 setup_ech.py <edk2-directory> <clang-path> <klee-path> [max-klee-time]
```
Example:
```
python3 setup_ech.py ../edk2-testcases-main /usr/lib/llvm-14/bin/clang /home/shafi/klee_build/bin/klee 5
```
This script will:

- Rewrite all #include <...> to absolute #include "..." paths for compatibility

- Comment out all STATIC_ASSERT() statements

- Save the configuration into a generated settings.py file containing:

 - Absolute path to the EDK2 source directory

 - Path to Clang compiler

 - Path to the KLEE binary

 - Optional: KLEE timeout (default: 5 seconds)

## Phase 2: Path Exploration Harnesses (PEH)
Run once per assertion (generated via static analysis)
```
python3 run_analysis.py \
  ../edk2-testcases-main/Testcases/Sample2Tests/CharConverter/CharConverter.c \
  146 \
  OOB_WRITE \
  "(*OutputBuffer)[OutIndex++] = 0x1B;"

```
 What this does:
- Checks if the assertion is already inserted

- If not, auto-inserts it at the specified line

- Generates a per-assertion KLEE driver for the relevant entrypoint (e.g., CharConverterEntryPoint)

- Compiles the instrumented file to LLVM bitcode

- Runs KLEE symbolic execution to explore relevant paths and check satisfiability of the assertion
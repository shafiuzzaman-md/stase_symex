#!/usr/bin/env python3

import os
import sys
import subprocess

# Load settings from stase_generated
sys.path.insert(0, os.path.abspath("../stase_generated"))
from settings import CLANG_PATH, KLEE_PATH, EDK2_PATH

OUT_DIR = "../stase_generated"
DRIVER_DIR = os.path.join(OUT_DIR, "generated_klee_drivers")
INSTRUMENTED_DIR = os.path.join(OUT_DIR, "instrumented_source")
STUB_HEADER = os.path.join(OUT_DIR, "global_stubs.h")
STUB_DEF = os.path.join(OUT_DIR, "global_stub_defs.c")

# Parse input arguments
if len(sys.argv) not in [5, 6]:
    print("Usage: python3 staseplusplus/run_analysis.py <driver.c> <target_source_file.c> <assertion_line_number> <assertion_expression> [<max_klee_time_seconds>]")
    sys.exit(1)

input_driver = sys.argv[1]
target_source_rel = sys.argv[2]
assertion_line = int(sys.argv[3])
assertion_text = sys.argv[4]
MAX_KLEE_TIME = int(sys.argv[5]) if len(sys.argv) == 6 else 5  # Default 5 seconds

# Paths
source_file = os.path.join(EDK2_PATH, target_source_rel)
driver_base = os.path.splitext(os.path.basename(input_driver))[0]
driver_obj = os.path.join(DRIVER_DIR, f"{driver_base}.bc")
bitcode_file = os.path.join(DRIVER_DIR, f"{driver_base}_final.bc")

# Ensure output directory exists
os.makedirs(DRIVER_DIR, exist_ok=True)

# Step 1: Insert assertion into instrumented target source if not already
instrumented_file = f"{os.path.splitext(source_file)[0]}_{assertion_line}_instrumented.c"

if not os.path.exists(instrumented_file):
    print("[+] Inserting assertion into target source...")
    with open(source_file, 'r') as f:
        lines = f.readlines()

    with open(instrumented_file, 'w') as f:
        for idx, line in enumerate(lines, 1):
            if idx == assertion_line:
                f.write(f"    {assertion_text}\n")
            f.write(line)
else:
    print("[✓] Assertion already inserted into target source.")

# Step 2: Compile driver (from inputs/) to .bc
print("[+] Compiling driver to LLVM bitcode...")
subprocess.run([
    CLANG_PATH, "-emit-llvm", "-c", "-g", "-O0",
    "-Xclang", "-disable-O0-optnone",
    input_driver,
    "-o", driver_obj
], check=True)

# Step 3: Compile global_stub_defs.c if exists
if os.path.exists(STUB_DEF):
    print("[+] Compiling stubs to LLVM bitcode...")
    stub_obj = os.path.join(DRIVER_DIR, "global_stub_defs.bc")
    subprocess.run([
        CLANG_PATH, "-emit-llvm", "-c", "-g", "-O0",
        "-Xclang", "-disable-O0-optnone",
        STUB_DEF,
        "-o", stub_obj
    ], check=True)

    # Step 4: Link driver and stubs into final .bc
    print("[+] Linking driver and stubs into final bitcode...")
    subprocess.run([
        "llvm-link", driver_obj, stub_obj, "-o", bitcode_file
    ], check=True)
else:
    # No stubs — just rename driver
    os.rename(driver_obj, bitcode_file)

# Step 5: Run KLEE symbolic execution
print(f"[+] Running KLEE symbolic execution with timeout {MAX_KLEE_TIME} seconds...")

def run_klee():
    return subprocess.run([
        KLEE_PATH, "--external-calls=all", "-libc=uclibc", "--posix-runtime",
        "--smtlib-human-readable", "--write-test-info", "--write-paths",
        "--write-smt2s", "--write-cov", "--write-cvcs", "--write-kqueries",
        "--write-sym-paths", "--only-output-states-covering-new",
        "--use-query-log=solver:smt2", "--simplify-sym-indices",
        f"-max-time={MAX_KLEE_TIME}",
        bitcode_file
    ])

run_klee()

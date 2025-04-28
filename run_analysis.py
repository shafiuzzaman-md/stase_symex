#!/usr/bin/env python3

import os
import sys
import subprocess

# Load settings from stase_generated
sys.path.insert(0, os.path.abspath("../stase_generated"))
from settings import CLANG_PATH, KLEE_PATH, EDK2_PATH

OUT_DIR = "../stase_generated"
DRIVER_DIR = os.path.join(OUT_DIR, "generated_klee_drivers")
STUB_HEADER = os.path.join(OUT_DIR, "global_stubs.h")
STUB_DEF = os.path.join(OUT_DIR, "global_stub_defs.c")
DRIVER_STUBS = os.path.join(OUT_DIR, "driver_stubs.c")

if len(sys.argv) != 6:
    print("Usage: python3 run_analysis.py <driver_template.c> <target_source_file.c> <assertion_line_number> <assertion_expression> <max_klee_time>")
    sys.exit(1)

input_driver = sys.argv[1]
target_source = sys.argv[2]
assertion_line = int(sys.argv[3])
assertion_text = sys.argv[4]
MAX_KLEE_TIME = int(sys.argv[5])

# Full path to the source file
source_file = os.path.join(EDK2_PATH, target_source)

base_name = os.path.splitext(os.path.basename(input_driver))[0]
driver_with_assertion = os.path.join(DRIVER_DIR, f"{base_name}_assert.c")
bitcode_file = os.path.join(DRIVER_DIR, f"{base_name}_assert.bc")

os.makedirs(DRIVER_DIR, exist_ok=True)

# Insert assertion into the target source file
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
    print("[✓] Assertion already inserted.")

# Insert assertion into the driver file
print("[+] Inserting assertion into driver...")
with open(input_driver, 'r') as f:
    lines = f.readlines()

with open(driver_with_assertion, 'w') as f:
    for line in lines:
        if "gImageHandle" in line and "gST" in line and "(" in line:
            f.write(f"    {assertion_text}\n")
        f.write(line)

print(f"[✓] Driver with assertion written to {driver_with_assertion}")

# Compile driver to LLVM bitcode
compile_sources = [driver_with_assertion]
if os.path.exists(STUB_DEF):
    compile_sources.append(STUB_DEF)

print("[+] Compiling to LLVM bitcode...")
subprocess.run([
    CLANG_PATH, "-emit-llvm", "-c", "-g", "-O0",
    "-Xclang", "-disable-O0-optnone",
    *compile_sources,
    "-o", bitcode_file
], check=True)

# Run KLEE symbolic execution
print("[+] Running KLEE symbolic execution...")
def run_klee():
    return subprocess.run([
        KLEE_PATH, "--external-calls=all", "-libc=uclibc", "--posix-runtime",
        "--smtlib-human-readable", "--write-test-info", "--write-paths",
        "--write-smt2s", "--write-cov", "--write-cvcs", "--write-kqueries",
        "--write-sym-paths", "--only-output-states-covering-new",
        "--use-query-log=solver:smt2", "--simplify-sym-indices",
        f"-max-time={MAX_KLEE_TIME}", bitcode_file
    ])

run_klee()

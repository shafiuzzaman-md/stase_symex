#!/usr/bin/env python3

import subprocess
import sys
import os

sys.path.insert(0, os.path.abspath("../stase_generated"))
from settings import CLANG_PATH, KLEE_PATH, EDK2_PATH

OUT_DIR = "../stase_generated"
DRIVER_DIR = os.path.join(OUT_DIR, "generated_klee_drivers")
STUB_HEADER = os.path.join(OUT_DIR, "global_stubs.h")
STUB_DEF = os.path.join(OUT_DIR, "global_stub_defs.c")

if len(sys.argv) != 6:
    print("Usage: python3 run_analysis.py <relative_source_path> <line_number> <vuln_type> <affected_instruction> <max_klee_time>")
    sys.exit(1)

relative_path = sys.argv[1]
line_number = sys.argv[2]
vuln_type = sys.argv[3]
affected_instruction = sys.argv[4]
MAX_KLEE_TIME = int(sys.argv[5])

source_file = os.path.join(EDK2_PATH, relative_path)

os.makedirs(DRIVER_DIR, exist_ok=True)

base_name = os.path.splitext(os.path.basename(source_file))[0]
entrypoint = base_name + "EntryPoint"
instrumented_file = f"{os.path.splitext(source_file)[0]}_{line_number}_{vuln_type}.c"
driver_file = os.path.join(DRIVER_DIR, f"klee_driver_{entrypoint}.c")
bitcode_file = os.path.join(DRIVER_DIR, f"klee_driver_{entrypoint}.bc")

# Insert assertion
if not os.path.exists(instrumented_file):
    print("[+] Inserting assertion...")
    subprocess.run(["python3", "insert_assertion.py", source_file, line_number, vuln_type, affected_instruction], check=True)
else:
    print("[✓] Assertion already inserted.")

# Generate driver
print("[+] Generating KLEE driver from instrumented file...")
subprocess.run(["python3", "generate_klee_driver.py", entrypoint, instrumented_file, "--out-dir", DRIVER_DIR], check=True)

# Compile driver + stub_defs
compile_sources = [driver_file]
if os.path.exists(STUB_DEF):
    compile_sources.append(STUB_DEF)

print("[+] Compiling LLVM bitcode...")
subprocess.run([
    CLANG_PATH, "-emit-llvm", "-c", "-g", "-O0", "-Xclang", "-disable-O0-optnone",
    *compile_sources, "-o", bitcode_file
], check=True)

# Run KLEE
def run_klee():
    return subprocess.run([
        KLEE_PATH, "--external-calls=all", "-libc=uclibc", "--posix-runtime",
        "--smtlib-human-readable", "--write-test-info", "--write-paths",
        "--write-smt2s", "--write-cov", "--write-cvcs", "--write-kqueries",
        "--write-sym-paths", "--only-output-states-covering-new",
        "--use-query-log=solver:smt2", "--simplify-sym-indices",
        f"-max-time={MAX_KLEE_TIME}", bitcode_file
    ])

print("[+] Running KLEE symbolic execution...")
klee_result = run_klee()

# Auto-stub globals if unresolved
if os.path.exists("klee-last/info"):
    print("[!] Checking for unresolved globals...")
    subprocess.run(["python3", "auto_stub_globals.py", "klee-last/info"])
    if os.path.exists(STUB_HEADER):
        print("[+] Recompiling with auto-generated global stubs...")

        with open(driver_file, 'r+') as f:
            content = f.read()
            if '#include "global_stubs.h"' not in content:
                f.seek(0, 0)
                f.write(f'#include "global_stubs.h"\n' + content)

        subprocess.run([
            CLANG_PATH, "-emit-llvm", "-c", "-g", "-O0", "-Xclang", "-disable-O0-optnone",
            *compile_sources, "-o", bitcode_file
        ], check=True)

        print("[+] Rerunning KLEE symbolic execution...")
        run_klee()

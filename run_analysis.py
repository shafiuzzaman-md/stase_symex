#!/usr/bin/env python3

import subprocess
import sys
import os
from settings import CLANG_PATH, KLEE_PATH, MAX_KLEE_TIME

if len(sys.argv) != 5:
    print("Usage: python3 run_analysis.py <source_file> <line_number> <vuln_type> <affected_instruction>")
    sys.exit(1)

source_file = sys.argv[1]
line_number = sys.argv[2]
vuln_type = sys.argv[3]
affected_instruction = sys.argv[4]

base_name = os.path.splitext(os.path.basename(source_file))[0]
entrypoint = base_name + "EntryPoint"

instrumented_file = f"{os.path.splitext(source_file)[0]}_{line_number}_{vuln_type}.c"
driver_file = f"generated_klee_drivers/klee_driver_{entrypoint}.c"
bitcode_file = f"klee_driver_{entrypoint}.bc"

if not os.path.exists(instrumented_file):
    print("[+] Inserting assertion...")
    subprocess.run(["./insert_assertion.py", source_file, line_number, vuln_type, affected_instruction], check=True)
else:
    print("[✓] Assertion already inserted.")

print("[+] Generating KLEE driver...")
subprocess.run(["python3", "generate_klee_driver.py", entrypoint, source_file], check=True)

print("[+] Compiling LLVM bitcode...")
subprocess.run([
    CLANG_PATH, "-emit-llvm", "-c", "-g", "-O0",
    "-Xclang", "-disable-O0-optnone",
    driver_file, "-o", bitcode_file
], check=True)

print("[+] Running KLEE symbolic execution...")
klee_result = subprocess.run([
    KLEE_PATH, "--external-calls=all", "-libc=uclibc", "--posix-runtime",
    "--smtlib-human-readable", "--write-test-info", "--write-paths",
    "--write-smt2s", "--write-cov", "--write-cvcs", "--write-kqueries",
    "--write-sym-paths", "--only-output-states-covering-new",
    "--use-query-log=solver:smt2", "--simplify-sym-indices",
    f"-max-time={MAX_KLEE_TIME}", bitcode_file
])

# Auto-stub globals if needed
if os.path.exists("klee-last/info"):
    print("[!] Checking for unresolved globals...")
    subprocess.run(["python3", "auto_stub_globals.py", "klee-last/info"])
    if os.path.exists("generated_klee_drivers/global_stubs.h"):
        print("[+] Recompiling with auto-generated global stubs...")
        with open(driver_file, 'r+') as f:
            content = f.read()
            if '#include "global_stubs.h"' not in content:
                f.seek(0, 0)
                f.write('#include "global_stubs.h"\n' + content)

        subprocess.run([
            CLANG_PATH, "-emit-llvm", "-c", "-g", "-O0",
            "-Xclang", "-disable-O0-optnone",
            driver_file, "-o", bitcode_file
        ], check=True)

        print("[+] Rerunning KLEE symbolic execution...")
        subprocess.run([
            KLEE_PATH, "--external-calls=all", "-libc=uclibc", "--posix-runtime",
            "--smtlib-human-readable", "--write-test-info", "--write-paths",
            "--write-smt2s", "--write-cov", "--write-cvcs", "--write-kqueries",
            "--write-sym-paths", "--only-output-states-covering-new",
            "--use-query-log=solver:smt2", "--simplify-sym-indices",
            f"-max-time={MAX_KLEE_TIME}", bitcode_file
        ])

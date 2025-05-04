#!/usr/bin/env python3

import os
import sys
import subprocess

# Load settings from stase_generated
sys.path.insert(0, os.path.abspath("../stase_generated"))
from settings import CLANG_PATH, KLEE_PATH

OUT_DIR = "../stase_generated"
DRIVER_DIR = os.path.join(OUT_DIR, "generated_klee_drivers")
STUB_DEF = os.path.join(OUT_DIR, "global_stub_defs.c")

# Parse input arguments
if len(sys.argv) not in [2, 3]:
    print("Usage: python3 run_analysis.py <driver.c> [<max_klee_time_seconds>]")
    sys.exit(1)

input_driver = sys.argv[1]
MAX_KLEE_TIME = int(sys.argv[2]) if len(sys.argv) == 3 else 5

# Paths
os.makedirs(DRIVER_DIR, exist_ok=True)
driver_base = os.path.splitext(os.path.basename(input_driver))[0]
driver_obj = os.path.join(DRIVER_DIR, f"{driver_base}.bc")

# Step 1: Compile driver to LLVM bitcode
print("[+] Compiling driver to LLVM bitcode...")
subprocess.run([
    CLANG_PATH, "-emit-llvm", "-c", "-g", "-O0",
    "-Xclang", "-disable-O0-optnone",
    input_driver,
    "-o", driver_obj
], check=True)

# Step 2: Run KLEE symbolic execution
print(f"[+] Running KLEE symbolic execution with timeout {MAX_KLEE_TIME} seconds...")

def run_klee():
    return subprocess.run([
        KLEE_PATH, "--external-calls=all", "-libc=uclibc", "--posix-runtime",
        "--smtlib-human-readable", "--write-test-info", "--write-paths",
        "--write-smt2s", "--write-cov", "--write-cvcs", "--write-kqueries",
        "--write-sym-paths", 
        "--use-query-log=solver:smt2", "--simplify-sym-indices",
        f"-max-time={MAX_KLEE_TIME}", "--kdalloc",
        driver_obj
    ])

run_klee()

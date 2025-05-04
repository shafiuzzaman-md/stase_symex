#!/usr/bin/env python3

import os
import sys
import subprocess
from glob import glob
from extract_signature import extract_and_combine
from parse_output import convert_file_to_json

# Load settings from stase_generated
sys.path.insert(0, os.path.abspath("../stase_generated"))
from settings import CLANG_PATH, KLEE_PATH

OUT_DIR = "../stase_generated"
DRIVER_DIR = os.path.join(OUT_DIR, "generated_klee_drivers")
OUTPUT_TXT_DIR = os.path.abspath(os.path.join(OUT_DIR, os.pardir, "stase_output"))
OUTPUT_JSON_DIR = os.path.abspath(os.path.join(OUT_DIR, os.pardir, "formatted_output"))

os.makedirs(OUTPUT_TXT_DIR, exist_ok=True)
os.makedirs(OUTPUT_JSON_DIR, exist_ok=True)

def compile_driver(input_driver):
    os.makedirs(DRIVER_DIR, exist_ok=True)
    base = os.path.basename(input_driver)
    name = os.path.splitext(base)[0]
    output_bc = os.path.join(DRIVER_DIR, f"{name}.bc")
    subprocess.run([
        CLANG_PATH, "-emit-llvm", "-c", "-g", "-O0", "-Xclang", "-disable-O0-optnone",
        input_driver, "-o", output_bc
    ], check=True)
    return name, output_bc

def run_klee(bitcode_file, timeout):
    subprocess.run([
        KLEE_PATH, "--external-calls=all", "-libc=uclibc", "--posix-runtime",
        "--smtlib-human-readable", "--write-test-info", "--write-paths", "--write-smt2s",
        "--write-cov", "--write-cvcs", "--write-kqueries", "--write-sym-paths",
        "--use-query-log=solver:smt2", "--simplify-sym-indices", "--kdalloc",
        f"-max-time={timeout}", bitcode_file
    ], check=True)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 run_analysis.py <driver.c> [timeout] | --batch")
        sys.exit(1)

    timeout = 5
    if sys.argv[1] == "--batch":
        drivers = glob("../inputs/klee_driver_*.c")
    else:
        drivers = [sys.argv[1]]
        if len(sys.argv) == 3:
            timeout = int(sys.argv[2])

    for driver in drivers:
        print(f"[+] Processing: {driver}")
        name, bc = compile_driver(driver)
        run_klee(bc, timeout)
        extract_and_combine(driver, f"{name}_output.txt")
        convert_file_to_json(os.path.join(OUTPUT_TXT_DIR, f"{name}_output.txt"), OUTPUT_JSON_DIR)
        print(f"[✓] Done: {name}\n")

if __name__ == "__main__":
    main()

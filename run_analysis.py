#!/usr/bin/env python3

import os
import sys
import subprocess
import argparse
from glob import glob
from extract_signature import extract_and_combine
from parse_output import convert_file_to_json

OUT_DIR = "../stase_generated"
DRIVER_DIR = os.path.join(OUT_DIR, "generated_klee_drivers")
OUTPUT_TXT_DIR = os.path.abspath(os.path.join(OUT_DIR, os.pardir, "stase_output"))
OUTPUT_JSON_DIR = os.path.abspath(os.path.join(OUT_DIR, os.pardir, "formatted_output"))

os.makedirs(OUTPUT_TXT_DIR, exist_ok=True)
os.makedirs(OUTPUT_JSON_DIR, exist_ok=True)

def compile_driver(input_driver, clang_path):
    os.makedirs(DRIVER_DIR, exist_ok=True)
    base = os.path.basename(input_driver)
    name = os.path.splitext(base)[0]
    output_bc = os.path.join(DRIVER_DIR, f"{name}.bc")
    subprocess.run([
        clang_path, "-emit-llvm", "-c", "-g", "-O0", "-Xclang", "-disable-O0-optnone",
        input_driver, "-o", output_bc
    ], check=True)
    return name, output_bc

def run_klee(bitcode_file, timeout, klee_path):
    subprocess.run([
        klee_path, "--external-calls=all", "-libc=uclibc", "--posix-runtime",
        "--smtlib-human-readable", "--write-test-info", "--write-paths", "--write-smt2s",
        "--write-cov", "--write-cvcs", "--write-kqueries", "--write-sym-paths",
        "--use-query-log=solver:smt2", "--simplify-sym-indices", "--kdalloc",
        f"-max-time={timeout}", bitcode_file
    ], check=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("driver", nargs="?", help="Input KLEE driver file or use --batch")
    parser.add_argument("--timeout", type=int, default=5, help="KLEE execution timeout in seconds")
    parser.add_argument("--batch", action="store_true", help="Run all drivers in batch mode")
    parser.add_argument("--clang-path", required=True, help="Path to clang binary")
    parser.add_argument("--klee-path", required=True, help="Path to klee binary")
    args = parser.parse_args()

    if args.batch:
        drivers = glob("../inputs/klee_driver_*.c")
    elif args.driver:
        drivers = [args.driver]
    else:
        print("[✗] Either --batch or <driver.c> must be specified")
        sys.exit(1)

    for driver in drivers:
        print(f"[+] Processing: {driver}")
        name, bc = compile_driver(driver, args.clang_path)
        run_klee(bc, args.timeout, args.klee_path)
        extract_and_combine(driver, f"{name}_output.txt")
        convert_file_to_json(os.path.join(OUTPUT_TXT_DIR, f"{name}_output.txt"), OUTPUT_JSON_DIR)
        print(f"[✓] Done: {name}\n")

if __name__ == "__main__":
    main()

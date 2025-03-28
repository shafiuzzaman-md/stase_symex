# run_analysis.py

import subprocess
import sys
import os

if len(sys.argv) != 5:
    print("Usage: python3 run_analysis.py <source_file> <line_number> <vuln_type> <affected_instruction>")
    sys.exit(1)

source_file = sys.argv[1]
line_number = sys.argv[2]
vuln_type = sys.argv[3]
affected_instruction = sys.argv[4]

base_name = os.path.splitext(os.path.basename(source_file))[0]
entrypoint = base_name + "EntryPoint"

print("[+] Inserting assertion...")
subprocess.run(["./insert_assertion.py", source_file, line_number, vuln_type, affected_instruction], check=True)

print("[+] Generating KLEE driver...")
subprocess.run(["python3", "generate_klee_driver.py", entrypoint, source_file], check=True)

bc_file = f"generated_klee_drivers/klee_driver_{entrypoint}.c"
bc_output = f"klee_driver_{entrypoint}.bc"

print("[+] Compiling LLVM bitcode...")
subprocess.run([
    "clang-14", "-emit-llvm", "-c", "-g", "-O0", 
    "-Xclang", "-disable-O0-optnone", bc_file, "-o", bc_output
], check=True)

print("[+] Running KLEE symbolic execution...")
subprocess.run([
    "klee", "--external-calls=all", "-libc=uclibc", "--posix-runtime",
    "--smtlib-human-readable", "--write-test-info", "--write-paths",
    "--write-smt2s", "--write-cov", "--write-cvcs", "--write-kqueries",
    "--write-sym-paths", "--only-output-states-covering-new",
    "--use-query-log=solver:smt2", "--simplify-sym-indices",
    "-max-time=5", bc_output
], check=True)

print("[✓] Analysis completed.")

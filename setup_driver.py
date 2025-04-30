#!/usr/bin/env python3

import os
import sys
import argparse
import re

from pathlib import Path

def extract_entrypoint_signature(entry_file, entrypoint_name):
    with open(entry_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Match function signature including multiline args
    pattern = re.compile(rf'{re.escape(entrypoint_name)}\s*\((.*?)\)', re.DOTALL)
    match = pattern.search(content)
    if not match:
        return [], []

    arg_string = match.group(1).strip().replace('\n', ' ')
    arg_list = [arg.strip() for arg in arg_string.split(',') if arg.strip()]

    declarations = []
    names = []
    for arg in arg_list:
        parts = arg.split()
        if not parts:
            continue
        name = parts[-1].replace("*", "").strip()
        decl = ' '.join(parts[:-1]) + ' ' + parts[-1]
        declarations.append(decl)
        names.append(name)
    return declarations, names

def extract_headers(entry_file):
    headers = []
    with open(entry_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#include') and '"' in line:
                headers.append(line)
    return headers

def main():
    parser = argparse.ArgumentParser(description="Generate a KLEE driver template for STASE analysis.")
    parser.add_argument("entrypoint_file", help="Relative path to source file containing the entrypoint function")
    parser.add_argument("entrypoint_name", help="Entrypoint function name (e.g., CharConverterEntryPoint)")
    parser.add_argument("vulnerability_type", help="Vulnerability type (e.g., OOB_WRITE)")
    parser.add_argument("assertion_line", help="Line number where the vulnerability is located")
    parser.add_argument("target_source_relative_path", help="Relative path to target source file inside source tree")
    parser.add_argument("--symbolic", nargs="*", help="List of symbolic variable declarations (e.g., 'uint8_t buf[16]')")
    parser.add_argument("--concrete", nargs="*", help="List of concrete initialization lines (e.g., 'gSmst = NULL;')")
    args = parser.parse_args()

    entry_file = args.entrypoint_file
    entrypoint = args.entrypoint_name
    vuln_type = args.vulnerability_type
    line_number = args.assertion_line
    target_source_rel = args.target_source_relative_path
    symbolic_vars = args.symbolic or []
    concrete_inits = args.concrete or []

    INPUTS_DIR = "../inputs"
    os.makedirs(INPUTS_DIR, exist_ok=True)

    driver_filename = f"klee_driver_{entrypoint}_{vuln_type}_{line_number}.c"
    driver_path = os.path.join(INPUTS_DIR, driver_filename)

    instrumented_source_path = os.path.join("../stase_generated/instrumented_source", target_source_rel)
    instrumented_dir = os.path.dirname(instrumented_source_path)

    entry_file_path = os.path.join("../stase_generated/instrumented_source", entry_file)
    headers = extract_headers(entry_file_path)
    param_decls, param_names = extract_entrypoint_signature(entry_file_path, entrypoint)

    with open(driver_path, "w") as f:
        f.write(f"// Auto-generated KLEE driver template for {entrypoint}\n")
        f.write(f"#include \"../stase_generated/global_stubs.h\"\n")
        f.write(f"#include \"../stase_generated/global_stub_defs.c\"\n")
        f.write(f"#include \"../stase_symex/klee/klee.h\"\n")
        f.write("#include <string.h>\n#include <stdlib.h>\n")

        for hdr in headers:
            hdr_path = hdr.split('"')[1] if '"' in hdr else None
            if hdr_path:
                full_path = os.path.normpath(os.path.join(instrumented_dir, hdr_path))
                rel_path = os.path.relpath(full_path, os.path.dirname(driver_path))
                f.write(f'#include \"{rel_path}\"\n')

        rel_entry_source = os.path.relpath(instrumented_source_path, os.path.dirname(driver_path))
        f.write(f"\n// Include the entrypoint source file\n")
        f.write(f'#include \"{rel_entry_source}\"\n\n')

        f.write("int main() {\n")

        if symbolic_vars:
            f.write("\n    // Symbolic variables\n")
            for decl in symbolic_vars:
                name = decl.split()[-1]
                name_for_symbolic = name.replace('[', '_').replace(']', '')
                if '[' in name:
                    f.write(f"    {decl};\n")
                    f.write(f"    klee_make_symbolic({name.split('[')[0]}, sizeof({name_for_symbolic}), \"{name_for_symbolic}\");\n")
                else:
                    f.write(f"    {decl};\n")
                    f.write(f"    klee_make_symbolic(&{name}, sizeof({name}), \"{name}\");\n")

        

        if param_decls:
            f.write("\n    // Entry point arguments\n")
            symbolic_names = {decl.split()[-1].split('[')[0] for decl in symbolic_vars}
            for decl in param_decls:
                name = decl.split()[-1].split('[')[0]
                if name not in symbolic_names:
                 f.write(f"    {decl};\n")


        if concrete_inits:
            f.write("\n    // Concrete initializations\n")
            for line in concrete_inits:
                f.write(f"    {line}\n")

        f.write("\n    // Call the entrypoint\n")
        if param_names:
            call_args = ', '.join(param_names)
            f.write(f"    {entrypoint}({call_args});\n")
        else:
            f.write(f"    {entrypoint}();\n")

        f.write("\n    return 0;\n")
        f.write("}\n")

    print(f"[✓] Driver template generated at: {driver_path}")

if __name__ == "__main__":
    main()

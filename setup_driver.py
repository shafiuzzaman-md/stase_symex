#!/usr/bin/env python3

import os
import sys
import argparse
import re

from pathlib import Path

def extract_entrypoint_signature(path, fname):
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        txt = f.read()
    m = re.search(rf'{re.escape(fname)}\s*\((.*?)\)', txt, re.DOTALL)
    if not m:
        return [], []
    arg_str = m.group(1).strip().replace('\n', ' ')
    arg_list = [a.strip() for a in arg_str.split(',') if a.strip()]
    decls, names = [], []
    for a in arg_list:
        parts = a.split()
        if not parts:
            continue
        name = parts[-1].replace('*', '').strip()
        decl  = ' '.join(parts[:-1]) + ' ' + parts[-1]
        decls.append(decl)
        names.append(name)
    return decls, names

def extract_headers(path):
    hdrs = []
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.strip().startswith('#include') and '"' in line:
                hdrs.append(line.strip())
    return hdrs

def main():
    ap = argparse.ArgumentParser("Generate KLEE driver")
    ap.add_argument("entrypoint_file")
    ap.add_argument("entrypoint_name")
    ap.add_argument("vulnerability_type")
    ap.add_argument("assertion_line")
    ap.add_argument("target_source_relative_path")
    ap.add_argument("--symbolic", nargs='*', default=[])
    ap.add_argument("--concrete", nargs='*', default=[])
    args = ap.parse_args()

    INPUTS = "../inputs"
    os.makedirs(INPUTS, exist_ok=True)

    driver_name = f"klee_driver_{args.entrypoint_name}_{args.vulnerability_type}_{args.assertion_line}.c"
    driver_path = os.path.join(INPUTS, driver_name)

    instr_src = os.path.join("../stase_generated/instrumented_source", args.target_source_relative_path)
    instr_dir = os.path.dirname(instr_src)
    entry_abs = os.path.join("../stase_generated/instrumented_source", args.entrypoint_file)

    headers = extract_headers(entry_abs)
    param_decls, param_names = extract_entrypoint_signature(entry_abs, args.entrypoint_name)

    sym_vars = args.symbolic
    conc_inits = args.concrete

    sym_names_set = {d.split()[-1].split('[')[0].replace('*','').strip() for d in sym_vars}

    with open(driver_path, 'w') as f:
        f.write(f"// Auto-generated KLEE driver for {args.entrypoint_name}\n")
        f.write('#include "../stase_generated/global_stubs.h"\n')
        f.write('#include "../stase_generated/global_stub_defs.c"\n')
        f.write('#include "../stase_symex/klee/klee.h"\n')
        f.write('#include <string.h>\n#include <stdlib.h>\n')
        f.write('#include "../stase_symex/uefi_helper_stubs.c"\n')
        # include headers
        for h in headers:
            hfile = h.split('"')[1]
            full  = os.path.normpath(os.path.join(instr_dir, hfile))
            rel   = os.path.relpath(full, os.path.dirname(driver_path))
            f.write(f'#include "{rel}"\n')

        rel_entry = os.path.relpath(instr_src, os.path.dirname(driver_path))
        f.write('\n// Instrumented entrypoint source\n')
        f.write(f'#include "{rel_entry}"\n\n')

        f.write('int main() {\n')

        # symbolic variables
        if sym_vars:
            f.write('    // Symbolic variables\n')
            for decl in sym_vars:
                raw_name = decl.split()[-1]
                base_name = raw_name.replace('[','_').replace(']','')
                if '[' in raw_name:  # array
                    f.write(f'    {decl};\n')
                    f.write(f'    klee_make_symbolic({raw_name.split("[")[0]}, sizeof({base_name}), "{base_name}");\n')
                elif '*' in decl:   # pointer -> malloc + pointee symbolic
                    base_type = ' '.join(decl.split()[:-1]).replace('*','').strip()
                    ptr_name  = raw_name.lstrip('*')
                    f.write(f'    {decl} = malloc(sizeof({base_type}));\n')
                    f.write(f'    klee_make_symbolic({ptr_name}, sizeof({base_type}), "{ptr_name}");\n')
                else:               # scalar
                    f.write(f'    {decl};\n')
                    f.write(f'    klee_make_symbolic(&{raw_name}, sizeof({raw_name}), "{raw_name}");\n')

        # param declarations not already symbolic
        if param_decls:
            f.write('\n    // Entrypoint parameters\n')
            for decl, name in zip(param_decls, param_names):
                if name not in sym_names_set:
                    if '*' in decl:
                        f.write(f'    {decl} = NULL;\n')
                    else:
                        f.write(f'    {decl} = 0;\n')

        # concrete initialisations
        if conc_inits:
            f.write('\n    // Concrete initialisations\n')
            for line in conc_inits:
                f.write(f'    {line}\n')

        # call entrypoint
        call_list = ', '.join(param_names)
        f.write('\n    // Call entrypoint\n')
        f.write(f'    {args.entrypoint_name}({call_list});\n')

        f.write('\n    return 0;\n')
        f.write('}\n')

    print(f"[✓] Driver generated at {driver_path}")

if __name__ == '__main__':
    main()

#!/usr/bin/env python3

import os
import argparse

def get_header_from_source(source_file, output_dir):
    source_abs = os.path.abspath(source_file)
    output_abs = os.path.abspath(output_dir)
    rel_path = os.path.relpath(source_abs, output_abs)
    return f'#include "{rel_path.replace(".c", ".h")}"'

def find_edk_root(path):
    path = os.path.abspath(path if os.path.isdir(path) else os.path.dirname(path))
    while path != "/" and not any(name.lower().startswith("mdepkg") for name in os.listdir(path)):
        path = os.path.dirname(path)
    return path

def generate_klee_driver(entrypoint, source_file, output_name=None):
    out_dir = "generated_klee_drivers"
    os.makedirs(out_dir, exist_ok=True)

    header_line = get_header_from_source(source_file, out_dir)
    source_include = f'#include "{os.path.relpath(source_file, out_dir)}"'
    out_file = os.path.join(out_dir, output_name or f'klee_driver_{entrypoint}.c')

    code = f"""// Auto-generated KLEE driver for {entrypoint}
#include "global_stubs.h"
#include "global_stub_defs.c"
#include "../klee/klee.h"
#include <string.h>
#include <stdlib.h>
{header_line}
{source_include}

int main() {{
    {entrypoint}(gImageHandle, gST);
    return 0;
}}
"""
    with open(out_file, "w") as f:
        f.write(code)

    print(f"[+] KLEE driver generated at: {out_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a KLEE driver for an entrypoint.")
    parser.add_argument("entrypoint", help="Entrypoint function (e.g., FooEntryPoint)")
    parser.add_argument("source_file", help="Path to source file (e.g., ../edk2-testcases/Foo.c)")
    parser.add_argument("--output", help="Optional output filename")
    args = parser.parse_args()

    generate_klee_driver(args.entrypoint, args.source_file, args.output)

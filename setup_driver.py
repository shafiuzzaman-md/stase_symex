#!/usr/bin/env python3

import os
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="Generate a KLEE driver template for STASE analysis.")
    parser.add_argument("entrypoint_name", help="Entrypoint function name (e.g., CharConverterEntryPoint)")
    parser.add_argument("vulnerability_type", help="Vulnerability type (e.g., OOB_WRITE)")
    parser.add_argument("assertion_line", help="Line number where the vulnerability is located")
    parser.add_argument("target_source_relative_path", help="Relative path to target source file inside source tree")
    parser.add_argument("--symbolic", nargs="*", help="List of symbolic variable declarations (e.g., 'uint8_t buf[16]')")
    parser.add_argument("--concrete", nargs="*", help="List of concrete initialization lines (e.g., 'gSmst = NULL;')")
    args = parser.parse_args()

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

    # Correct path for instrumented source
    instrumented_source_path = os.path.join("../stase_generated/instrumented_source", target_source_rel)

    with open(driver_path, "w") as f:
        f.write(f"""// Auto-generated KLEE driver template for {entrypoint}
#include "../stase_generated/global_stubs.h"
#include "../stase_generated/global_stub_defs.c"
#include "../staseplusplus/klee/klee.h"
#include <string.h>
#include <stdlib.h>

// Include the instrumented target source
#include "{instrumented_source_path}"

int main() {{
    initialize_stubs();
""")

        if symbolic_vars:
            f.write("\n    // Symbolic variables\n")
            for decl in symbolic_vars:
                name = decl.split()[-1]
                name_for_symbolic = name.replace('[', '_').replace(']', '')
                if '[' in name:
                    # Array
                    f.write(f"    {decl};\n")
                    f.write(f"    klee_make_symbolic({name.split('[')[0]}, sizeof({name_for_symbolic}), \"{name_for_symbolic}\");\n")
                else:
                    # Normal variable
                    f.write(f"    {decl};\n")
                    f.write(f"    klee_make_symbolic(&{name}, sizeof({name}), \"{name}\");\n")

        if concrete_inits:
            f.write("\n    // Concrete initializations\n")
            for line in concrete_inits:
                f.write(f"    {line}\n")

        f.write(f"""

    // Call the entrypoint
    {entrypoint}(gImageHandle, gST);

    return 0;
}}
""")

    print(f"[✓] Driver template generated at: {driver_path}")

if __name__ == "__main__":
    main()

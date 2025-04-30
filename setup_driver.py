#!/usr/bin/env python3
"""
Generate a KLEE driver template that already:
  • includes global-stubs + helper stubs
  • inserts all #include dependencies
  • allocates / makes-symbolic every --symbolic var
  • declares entry-point parameters
"""

import os
import re
import argparse
from pathlib import Path

# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
PROTO_RE = r'{}\s*\((.*?)\)'          # filled with entry-point name


def extract_signature(src: Path, fname: str):
    """Return (declarations[], names[]) for the entry-point parameters."""
    txt = src.read_text(errors='ignore')
    m = re.search(PROTO_RE.format(re.escape(fname)), txt, re.DOTALL)
    if not m:
        return [], []

    arg_list = [a.strip() for a in m.group(1).replace('\n', ' ').split(',')
                if a.strip()]
    decls, names = [], []
    for arg in arg_list:
        bits = arg.split()
        if not bits:
            continue
        decl  = ' '.join(bits[:-1]) + ' ' + bits[-1]
        name  = bits[-1].lstrip('*').rstrip('[]')
        decls.append(decl)
        names.append(name)
    return decls, names


def header_includes(src: Path):
    """All local #include "foo.h" lines in *src*."""
    hdrs = []
    for line in src.read_text(errors='ignore').splitlines():
        line = line.strip()
        if line.startswith('#include') and '"' in line:
            hdrs.append(line)
    return hdrs


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser("Generate driver skeleton")
    ap.add_argument("entrypoint_file")              # relative to source tree
    ap.add_argument("entrypoint_name")              # e.g. Iconv
    ap.add_argument("vuln_type")                    # e.g. OOB_WRITE
    ap.add_argument("assert_line")                  # 146
    ap.add_argument("target_source_rel")            # relative .c for assert
    ap.add_argument("--symbolic", nargs='*', default=[])
    ap.add_argument("--concrete", nargs='*', default=[])
    args = ap.parse_args()

    INPUT_DIR = Path("../inputs")
    INPUT_DIR.mkdir(exist_ok=True)

    drv_name = f"klee_driver_{args.entrypoint_name}_{args.vuln_type}_{args.assert_line}.c"
    drv_path = INPUT_DIR / drv_name

    # Paths inside stase_generated
    SG           = Path("../stase_generated")
    SRC_ROOT     = SG / "instrumented_source"
    entry_abs    = SRC_ROOT / args.entrypoint_file
    target_abs   = SRC_ROOT / args.target_source_rel
    includes_dir = target_abs.parent

    # ---- gather information ------------------------------------------------
    hdr_lines          = header_includes(entry_abs)
    param_decls, pnames = extract_signature(entry_abs, args.entrypoint_name)

    sym_decl_set = {d.split()[-1].lstrip('*').split('[')[0] for d in args.symbolic}

    # ---- write driver ------------------------------------------------------
    with drv_path.open('w') as f:
        write = f.write
        write(f"// Auto-generated KLEE driver for {args.entrypoint_name}\n")
        write('#include "../stase_generated/global_stubs.h"\n')
        write('#include "../stase_generated/global_stub_defs.c"\n')
        write('#include "../stase_symex/uefi_helper_stubs.c"\n')
        write('#include "../stase_symex/klee/klee.h"\n')
        write('#include <string.h>\n#include <stdlib.h>\n')

        # local header dependencies
        for inc in hdr_lines:
            hdr_file = inc.split('"')[1]
            full     = (includes_dir / hdr_file).resolve()
            rel      = os.path.relpath(full, drv_path.parent)
            write(f'#include "{rel}"\n')

        # entrypoint .c file itself
        rel_entry_c = os.path.relpath(target_abs, drv_path.parent)
        write("\n// Instrumented entrypoint source\n")
        write(f'#include "{rel_entry_c}"\n\n')

        # ---------- main() -------------
        write("int main(void) {\n")

        # -- symbolic (user-supplied) --
        if args.symbolic:
            write("    // Symbolic variables\n")
            for decl in args.symbolic:
                raw      = decl.split()[-1]
                base_nm  = raw.lstrip('*').replace('[', '_').replace(']', '')
                if '[' in raw:                           # array
                    write(f"    {decl};\n")
                    write(f"    klee_make_symbolic({raw.split('[')[0]}, "
                          f"sizeof({base_nm}), \"{base_nm}\");\n")
                elif '**' in decl:                       # double pointer
                    base_t = ' '.join(decl.split()[:-1]).replace('*', '').strip()
                    ptr_nm = raw.lstrip('*')
                    write(f"    {decl} = malloc(sizeof({base_t} *));\n")
                    write(f"    klee_make_symbolic({ptr_nm}, sizeof({base_t} *), "
                          f"\"{ptr_nm}\");\n")
                elif '*' in decl:                        # single pointer
                    base_t = ' '.join(decl.split()[:-1]).replace('*', '').strip()
                    ptr_nm = raw.lstrip('*')
                    write(f"    {decl} = malloc(sizeof({base_t}));\n")
                    write(f"    klee_make_symbolic({ptr_nm}, sizeof({base_t}), "
                          f"\"{ptr_nm}\");\n")
                else:                                    # scalar
                    write(f"    {decl};\n")
                    write(f"    klee_make_symbolic(&{raw}, sizeof({raw}), "
                          f"\"{raw}\");\n")

        # -- parameters not already symbolic --
        if param_decls:
            write("\n    // Entrypoint parameters\n")
            for decl, nm in zip(param_decls, pnames):
                if nm not in sym_decl_set:
                    if '*' in decl:
                        write(f"    {decl} = NULL;\n")
                    else:
                        write(f"    {decl} = 0;\n")

        # -- concrete initialisation --
        if args.concrete:
            write("\n    // Concrete initialisations\n")
            for line in args.concrete:
                write(f"    {line}\n")

        # -- call entrypoint --
        call_args = ', '.join(pnames)
        write("\n    // Call entrypoint\n")
        write(f"    {args.entrypoint_name}({call_args});\n")

        write("\n    return 0;\n")
        write("}\n")

    # --- final message ---------------------------------------------------
    try:
        pretty = drv_path.relative_to(Path.cwd())
    except ValueError:
        pretty = drv_path.resolve()
    print(f"[✓] Driver generated -> {pretty}")



if __name__ == "__main__":
    main()

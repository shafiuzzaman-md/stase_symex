#!/usr/bin/env python3
"""
setup_driver.py – generate a KLEE driver (assertion instrumentation removed)

Mandatory flags
---------------
--entry-src   <rel-path>   C file that contains the entry-point
--entry-func  <symbol>     Entry-point function name (e.g. Iconv)
--vuln        <OOB_WRITE|WWW|CFH>
--assert-line <N>          Line number for naming only (assertion is not inserted)
--target-src  <rel-path>   Source file related to the driver (used for header includes)

Optional / repeatable
---------------------
--symbolic "type name"           (in main)
--concrete "stmt;"               (emitted inside main)
--global   "type name"           (file-scope declaration before main)
--malloc PTR SZ                 (preallocate inner buffer for T**)
--default-malloc <size|0>       (default allocation size for any T** without explicit malloc)
"""

import argparse, os, re
from pathlib import Path

SIG_RE = r'{}\s*\((.*?)\)'  # filled with entry-func

def sig_info(src: Path, fn: str):
    txt = src.read_text(errors='ignore')
    m = re.search(SIG_RE.format(re.escape(fn)), txt, re.DOTALL)
    if not m:
        return [], []
    args = [a.strip() for a in m.group(1).replace('\n', ' ').split(',') if a.strip()]
    decls, names = [], []
    for a in args:
        parts = a.split()
        decls.append(' '.join(parts[:-1]) + ' ' + parts[-1])
        names.append(parts[-1].lstrip('*').rstrip('[]'))
    return decls, names

def local_hdrs(src: Path):
    return [l.strip() for l in src.read_text(errors='ignore').splitlines()
            if l.strip().startswith('#include') and '"' in l]

def main():
    ap = argparse.ArgumentParser("Generate driver only (no assertion insertion)")
    req = ap.add_argument_group("required")
    req.add_argument("--entry-src", required=True)
    req.add_argument("--entry-func", required=True)
    req.add_argument("--vuln", required=True)
    req.add_argument("--assert-line", required=True, type=int)
    req.add_argument("--target-src", required=True)

    rep = ap.add_argument_group("repeatable / optional")
    rep.add_argument("--symbolic", action='append', default=[])
    rep.add_argument("--concrete", action='append', default=[])
    rep.add_argument("-g", "--global", dest="globals_", action='append', default=[])
    rep.add_argument("--malloc", nargs=2, action='append', default=[])
    rep.add_argument("--default-malloc", type=int, default=0)

    args = ap.parse_args()

    malloc_map = {ptr: int(sz) for ptr, sz in args.malloc}

    sg_root = Path("../stase_generated_last")
    src_root = sg_root / "instrumented_source"
    entry_abs = src_root / args.entry_src
    target_abs = src_root / args.target_src

    inputs_dir = Path("../inputs"); inputs_dir.mkdir(exist_ok=True)
    drv_path = inputs_dir / f"klee_driver_{args.entry_func}_{args.vuln}_{args.assert_line}.c"

    hdrs, pnam = sig_info(entry_abs, args.entry_func)
    pdecl, _ = sig_info(entry_abs, args.entry_func)

    glob_set = {d.split()[-1].lstrip('*').split('[')[0] for d in args.globals_}
    sym_set = {d.split()[-1].lstrip('*').split('[')[0] for d in args.symbolic}

    inc_dir = target_abs.parent

    with drv_path.open('w') as f:
        W = f.write
        W(f"// Auto-generated driver for {args.entry_func}\n")

        edk_headers = [
            ("../stase_generated_last/global_stubs.h", sg_root / "global_stubs.h"),
            ("../stase_generated_last/global_stub_defs.c", sg_root / "global_stub_defs.c"),
            ("../stase_generated_last/uefi_helper_stubs.c", sg_root / "uefi_helper_stubs.c")
        ]
        for inc_str, inc_path in edk_headers:
            if inc_path.exists():
                W(f'#include "{inc_str}"\n')

        W('#include "../stase_symex/klee/klee.h"\n')
        W('#include <string.h>\n#include <stdlib.h>\n')

        for inc in local_hdrs(entry_abs):
            hdr = inc.split('"')[1]
            W(f'#include "{os.path.relpath((inc_dir / hdr).resolve(), drv_path.parent)}"\n')

        if args.globals_:
            W('\n// ----- user globals -----\n')
            for g in args.globals_:
                W(f'{g};\n')

        W('\n// Instrumented entry-point source\n')
        W(f'#include "{os.path.relpath(target_abs, drv_path.parent)}"\n\n')

        W('int main(void) {\n')

        if args.symbolic:
            W('    // Symbolic variables\n')
            for decl in args.symbolic:
                raw = decl.split()[-1]
                base = raw.lstrip('*').replace('[', '_').replace(']', '')
                if '[' in raw:
                    W(f'    {decl};\n')
                    W(f'    klee_make_symbolic({raw.split("[")[0]}, sizeof({base}), "{base}");\n')
                elif '**' in decl:
                    base_t = ' '.join(decl.split()[:-1]).replace('*', '').strip()
                    ptr_nm = raw.lstrip('*')
                    inner_sz = malloc_map.get(ptr_nm, args.default_malloc)
                    W(f'    {decl} = malloc(sizeof({base_t} *));\n')
                    if inner_sz:
                        W(f'    *{ptr_nm} = malloc({inner_sz});\n')
                        W(f'    klee_make_symbolic(*{ptr_nm}, {inner_sz}, "{ptr_nm}_data");\n')
                    W(f'    klee_make_symbolic({ptr_nm}, sizeof({base_t} *), "{ptr_nm}");\n')
                elif '*' in decl:
                    base_t = ' '.join(decl.split()[:-1]).replace('*', '').strip()
                    ptr_nm = raw.lstrip('*')
                    malloc_sz = malloc_map.get(ptr_nm, None)
                    if malloc_sz:
                        W(f'    {decl} = malloc({malloc_sz});\n')
                        W(f'    klee_make_symbolic({ptr_nm}, {malloc_sz}, "{ptr_nm}");\n')
                    else:
                        W(f'    {decl} = malloc(sizeof({base_t}));\n')
                        W(f'    klee_make_symbolic({ptr_nm}, sizeof({base_t}), "{ptr_nm}");\n')
                else:
                    if raw not in glob_set:
                        W(f'    {decl};\n')
                    W(f'    klee_make_symbolic(&{raw}, sizeof({raw}), "{raw}");\n')

        if pdecl:
            W('\n    // Entry-point parameters (default init)\n')
            for d, n in zip(pdecl, pnam):
                if n not in sym_set and n not in glob_set:
                    default_val = "NULL" if "*" in d else "0"
                    W(f'    {d} = {default_val};\n')


        if args.concrete:
            W('\n    // Concrete initialisation / constraints\n')
            for stmt in args.concrete:
                W(f'    {stmt}\n')

        W('\n    // Call entry-point\n')
        W(f'    {args.entry_func}({", ".join(pnam)});\n')
        W('    return 0;\n}\n')

    print(f"[✓] Driver  : {drv_path.resolve()}")
    rel_t = target_abs.relative_to(sg_root)

if __name__ == "__main__":
    main()

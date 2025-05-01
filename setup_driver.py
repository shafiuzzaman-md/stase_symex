#!/usr/bin/env python3
"""
setup_driver.py – generate a KLEE driver *and* inject a user-supplied
assertion in an instrumented source file.

Mandatory flags
---------------
--entry-src   <rel-path>   C file that contains the entry-point
--entry-func  <symbol>     Entry-point function name (e.g. Iconv)
--vuln        <OOB_WRITE|WWW|CFH>
--assert-line <N>          Line (in --target-src) to put the assertion *before*
--target-src  <rel-path>   Source file where assertion goes
--assertion   "<expr>"     Expression for klee_assert(...)

Optional / repeatable
---------------------
--symbolic "type name"           (in main)
--concrete "stmt;"               (emitted inside main)
--global   "type name"           (file-scope declaration before main)

Example
-------
python3 setup_driver.py \\
  --entry-src   Testcases/Sample2Tests/CharConverter/CharConverter.c \\
  --entry-func  Iconv \\
  --vuln        OOB_WRITE \\
  --assert-line 146 \\
  --target-src  Testcases/Sample2Tests/CharConverter/CharConverter.c \\
  -g          "unsigned OutputBuffer_cap" \\
  --symbolic  "unsigned OutputBuffer_cap" "CHAR8 **OutputBuffer" \\
  --concrete  "*OutputBuffer = malloc(OutputBuffer_cap);" \\
              "klee_make_symbolic(*OutputBuffer, OutputBuffer_cap, \\\"OutputBuffer_data\\\");" \\
              "klee_assume(OutputBuffer_cap>=1 && OutputBuffer_cap<=4096);" \\
  --assertion "OutIndex < OutputBuffer_cap"
"""

import argparse, os, re
from pathlib import Path

SIG_RE = r'{}\s*\((.*?)\)'          # filled with entry-func


# ---------------------------------------------------------------- helpers
def sig_info(src: Path, fn: str):
    txt = src.read_text(errors='ignore')
    m   = re.search(SIG_RE.format(re.escape(fn)), txt, re.DOTALL)
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


def clean_old_asserts(path: Path):
    """
    Remove every line that already contains a KLEE assertion.
    Called before we splice-in the fresh assertion so we never double-instrument.
    """
    src = path.read_text(errors='ignore').splitlines()
    cleaned = [ln for ln in src if "klee_assert(" not in ln]
    if len(cleaned) != len(src):
        path.write_text("\n".join(cleaned))

def inject_assert(path: Path, ln: int, expr: str):
    """
    • drop any previous klee_assert(...) lines first
    • then insert  '    klee_assert(expr);'  **before** the 1-based line <ln>
    """
    clean_old_asserts(path)

    lines = path.read_text(errors='ignore').splitlines()
    # avoid duplicate insert of exactly the same assertion text
    if any(expr in L for L in lines):
        return

    insert_at = max(0, ln - 1)          # convert 1-based → 0-based, keep ≥0
    lines.insert(insert_at, f"    klee_assert({expr});")
    path.write_text("\n".join(lines))


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser("Generate driver + inject assertion")
    req = ap.add_argument_group("required")
    req.add_argument("--entry-src",   required=True)
    req.add_argument("--entry-func",  required=True)
    req.add_argument("--vuln",        required=True,
                     choices=["OOB_WRITE", "WWW", "CFH"])
    req.add_argument("--assert-line", required=True, type=int)
    req.add_argument("--target-src",  required=True)
    req.add_argument("--assertion",   required=True)

    rep = ap.add_argument_group("repeatable / optional")
    rep.add_argument("--symbolic", action='append', default=[],
                     help='declare symbolic var inside main()')
    rep.add_argument("--concrete", action='append', default=[],
                     help='verbatim stmt inside main()')
    rep.add_argument("-g", "--global", dest="globals_", action='append',
                     default=[], help='file-scope declaration')

    args = ap.parse_args()

    sg_root   = Path("../stase_generated")
    src_root  = sg_root / "instrumented_source"
    entry_abs = src_root / args.entry_src
    target_abs= src_root / args.target_src

    # ---------------------------------------------------------------- assert
    inject_assert(target_abs, args.assert_line, args.assertion)

    # ---------------------------------------------------------------- driver
    inputs_dir = Path("../inputs"); inputs_dir.mkdir(exist_ok=True)
    drv_path   = inputs_dir / f"klee_driver_{args.entry_func}_{args.vuln}_{args.assert_line}.c"

    hdrs        = local_hdrs(entry_abs)
    pdecl, pnam = sig_info(entry_abs, args.entry_func)

    glob_set = {d.split()[-1].lstrip('*').split('[')[0] for d in args.globals_}
    sym_set  = {d.split()[-1].lstrip('*').split('[')[0] for d in args.symbolic}

    inc_dir = target_abs.parent

    with drv_path.open('w') as f:
        W = f.write
        # ------- includes --------------------------------------------------
        W(f"// Auto-generated driver for {args.entry_func}\n")
        W('#include "../stase_generated/global_stubs.h"\n')
        W('#include "../stase_generated/global_stub_defs.c"\n')
        W('#include "../stase_symex/uefi_helper_stubs.c"\n')
        W('#include "../stase_symex/klee/klee.h"\n')
        W('#include <string.h>\n#include <stdlib.h>\n')

        for inc in hdrs:
            hdr = inc.split('"')[1]
            W(f'#include "{os.path.relpath((inc_dir / hdr).resolve(), drv_path.parent)}"\n')

        # ------- user-requested globals -----------------------------------
        if args.globals_:
            W('\n// ----- user globals -----\n')
            for g in args.globals_:
                W(f'{g};\n')

        # ------- instrumented source --------------------------------------
        W('\n// Instrumented entry-point source\n')
        W(f'#include "{os.path.relpath(target_abs, drv_path.parent)}"\n\n')

        # =========================  main() ================================
        W('int main(void) {\n')

        # --- symbolic declarations ---------------------------------------
        if args.symbolic:
            W('    // Symbolic variables\n')
            for decl in args.symbolic:
                raw  = decl.split()[-1]
                base = raw.lstrip('*').replace('[', '_').replace(']', '')
                if '[' in raw:
                    W(f'    {decl};\n')
                    W(f'    klee_make_symbolic({raw.split("[")[0]}, sizeof({base}), "{base}");\n')
                elif '**' in decl:
                    base_t = ' '.join(decl.split()[:-1]).replace('*', '').strip()
                    ptr_nm = raw.lstrip('*')
                    W(f'    {decl} = malloc(sizeof({base_t} *));\n')
                    W(f'    klee_make_symbolic({ptr_nm}, sizeof({base_t} *), "{ptr_nm}");\n')
                elif '*' in decl:
                    base_t = ' '.join(decl.split()[:-1]).replace('*', '').strip()
                    ptr_nm = raw.lstrip('*')
                    W(f'    {decl} = malloc(sizeof({base_t}));\n')
                    W(f'    klee_make_symbolic({ptr_nm}, sizeof({base_t}), "{ptr_nm}");\n')
                else:
                    # scalar; decl may already exist globally – skip re-decl
                    if raw not in glob_set:
                        W(f'    {decl};\n')
                    W(f'    klee_make_symbolic(&{raw}, sizeof({raw}), "{raw}");\n')

        # --- entry-point parameters --------------------------------------
        if pdecl:
            W('\n    // Entry-point parameters (default init)\n')
            for d, n in zip(pdecl, pnam):
                if n not in sym_set and n not in glob_set:
                    W(f'    {d} = {"NULL" if "*" in d else "0"};\n')

        # --- concrete user statements ------------------------------------
        if args.concrete:
            W('\n    // Concrete initialisation / constraints\n')
            for stmt in args.concrete:
                W(f'    {stmt}\n')

        # --- call ---------------------------------------------------------
        W('\n    // Call entry-point\n')
        W(f'    {args.entry_func}({", ".join(pnam)});\n')
        W('    return 0;\n}\n')

    # ---------------------------------------------------------------- info
    print(f"[✓] Driver  : {drv_path.resolve()}")
    rel_t = target_abs.relative_to(sg_root)
    print(f"[✓] Assert  : inserted before line {args.assert_line} in {rel_t}")

# -------------------------------------------------------------------------
if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
setup_kernel_environment.py
Copy + prepare a Linux / kernel source tree for STASE_SYMEX.
Usage:
    python3 setup_kernel_environment.py <kernel-src-dir> <clang-path> <klee-path>
Produces:
    stase_generated/
        ├── instrumented_source/   (rewritten kernel tree)
        ├── kernel_stub_defs.c
        ├── kernel_stubs.h
        └── settings.py
"""

import os, sys, shutil, re, pathlib, subprocess, textwrap

OUT_ROOT   = pathlib.Path("../stase_generated").resolve()
SRC_OUT    = OUT_ROOT / "instrumented_source"
STUB_C     = OUT_ROOT / "kernel_stub_defs.c"
STUB_H     = OUT_ROOT / "kernel_stubs.h"

# ---------------------------------------------------------------------------
def rewrite_includes(root: pathlib.Path):
    """Turn  #include <foo.h>  that refer to *project-local* headers into "…". """
    local_hdr = {p.name for p in root.rglob("*.h")}             # header file set
    for path in root.rglob("*.c"):
        txt, changed = [], False
        for ln in path.read_text(errors="ignore").splitlines():
            m = re.match(r'\s*#\s*include\s*<([^>]+)>', ln)
            if m and m.group(1) in local_hdr:
                ln = re.sub(r'<([^>]+)>', r'"\1"', ln)
                changed = True
            txt.append(ln)
        if changed:
            path.write_text("\n".join(txt))

# ---------------------------------------------------------------------------
def extract_and_stub(root: pathlib.Path):
    """
    Find undefined globals / functions and emit weak stubs so KLEE links.
    Very lightweight: scans *.c for 'extern' & global declarations without def.
    """
    externs, defs = set(), set()
    sym_re = re.compile(r'\b([A-Za-z_]\w+)\b')
    for c in root.rglob("*.c"):
        src = c.read_text(errors="ignore")
        for m in re.finditer(r'\bextern\s+[^;]+?\b([A-Za-z_]\w+)\b', src):
            externs.add(m.group(1))
        # crude: record names that have a body  foo(...)  {   }
        for m in re.finditer(r'\b([A-Za-z_]\w+)\s*\([^;]*?\)\s*\{', src):
            defs.add(m.group(1))
        # globals with initialiser   int foo = …
        for m in re.finditer(r'\b([A-Za-z_]\w+)\s*=', src):
            defs.add(m.group(1))

    undefined = externs - defs
    if not undefined:
        return

    STUB_H.write_text("// Auto-generated kernel stub declarations\n")
    STUB_C.write_text("// Auto-generated kernel stub definitions\n")
    with STUB_H.open("a") as hh, STUB_C.open("a") as cc:
        for sym in sorted(undefined):
            hh.write(f"void {sym}(void);\n")
            cc.write(textwrap.dedent(f"""
            /* weak stub */  __attribute__((weak))
            void {sym}(void) {{ /* nop */ }}
            """))
    print(f"[✓] emitted {len(undefined)} weak stubs → {STUB_H.name} / {STUB_C.name}")

# ---------------------------------------------------------------------------
def write_settings(kernel_path, clang, klee):
    OUT_ROOT.mkdir(exist_ok=True)
    (OUT_ROOT / "settings.py").write_text(
        f'KERNEL_PATH = r"{kernel_path}"\n'
        f'CLANG_PATH  = r"{clang}"\n'
        f'KLEE_PATH   = r"{klee}"\n')
    print("[✓] settings.py written")

# ---------------------------------------------------------------------------
def main():
    if len(sys.argv) != 4:
        sys.exit("Usage: setup_kernel_environment.py <kernel-src> <clang> <klee>")

    src_dir, clang, klee = map(pathlib.Path, sys.argv[1:])
    if not src_dir.is_dir():   sys.exit(f"[!] kernel source dir not found: {src_dir}")
    if not clang.is_file():    sys.exit(f"[!] clang not found: {clang}")
    if not klee.is_file():     sys.exit(f"[!] klee not found:  {klee}")

    # fresh copy
    if SRC_OUT.exists(): shutil.rmtree(SRC_OUT)
    shutil.copytree(src_dir, SRC_OUT, symlinks=True)
    print(f"[✓] copied kernel tree → {SRC_OUT}")

    rewrite_includes(SRC_OUT)
    print("[✓] local #include <> → \"\" rewrite done")

    extract_and_stub(SRC_OUT)

    write_settings(SRC_OUT, clang, klee)
    print("[✓] Kernel environment ready for STASE_SYMEX!")

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()

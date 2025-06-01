#!/usr/bin/env python3
"""
instrument.py – inject a klee_assert and optionally stub functions or comment irrelevant statements

Usage:
-------
python3 instrument.py \
    --target-src <rel-path> \
    --assert-line <line-number> \
    --assertion "<expr>" \
    [--comment-lines 101 102 103 ...] \
    [--stub-functions foo bar ...]

Modifies file under:
  ../stase_generated_last/instrumented_source/<target-src>
  Uses and maintains: <target-src>.orig.c as a clean backup
"""

import argparse
from pathlib import Path
import re
import shutil

def ensure_backup(target_path: Path):
    backup_path = target_path.with_suffix(target_path.suffix + ".orig.c")
    if not backup_path.exists():
        shutil.copy2(target_path, backup_path)
        print(f"[✓] Saved original backup: {backup_path.relative_to(target_path.parent)}")
    else:
        shutil.copy2(backup_path, target_path)
        print(f"[→] Restored from backup before instrumentation: {target_path.name}")

def clean_old_asserts(path: Path):
    lines = path.read_text(errors='ignore').splitlines()
    cleaned = [ln for ln in lines if "klee_assert(" not in ln]
    if len(cleaned) != len(lines):
        path.write_text("\n".join(cleaned))

def inject_assert(path: Path, line: int, expr: str):
    clean_old_asserts(path)
    lines = path.read_text(errors='ignore').splitlines()
    if any(expr in L for L in lines):
        print(f"[!] Expression already exists in {path.name}, skipping.")
        return
    insert_at = max(0, line - 1)
    lines.insert(insert_at, f"    klee_assert({expr});")
    path.write_text("\n".join(lines))
    print(f"[✓] Inserted klee_assert at line {line} in {path}")

def comment_out_lines(path: Path, line_nums):
    lines = path.read_text(errors='ignore').splitlines()
    modified = False
    for ln in line_nums:
        if 0 <= ln - 1 < len(lines) and not lines[ln - 1].strip().startswith('//'):
            lines[ln - 1] = '// ' + lines[ln - 1]
            modified = True
    if modified:
        path.write_text("\n".join(lines))
        print(f"[✓] Commented out lines: {line_nums}")

def stub_functions(path: Path, fn_names):
    code = path.read_text(errors='ignore')
    stubbed = False
    for fn in fn_names:
        # Match function definition: int foo(...) { ... }
        fn_def_pattern = re.compile(rf'\b[a-zA-Z_][a-zA-Z0-9_]*\s+{fn}\s*\([^)]*\)\s*\{{', re.MULTILINE)
        matches = list(fn_def_pattern.finditer(code))
        for match in matches:
            start = match.start()
            # naive brace matching to find the body
            body_start = code.find('{', start)
            count = 1
            i = body_start + 1
            while i < len(code) and count > 0:
                if code[i] == '{':
                    count += 1
                elif code[i] == '}':
                    count -= 1
                i += 1
            stub_body = f'{{ /* stubbed {fn} */ return 0; }}'
            code = code[:body_start] + stub_body + code[i:]
            stubbed = True
    if stubbed:
        path.write_text(code)
        print(f"[✓] Stubbed functions: {fn_names}")

def main():
    ap = argparse.ArgumentParser("Patch source file for KLEE")
    ap.add_argument("--target-src", required=True, help="Path to target C file inside instrumented_source")
    ap.add_argument("--assert-line", type=int, help="Line to insert klee_assert before")
    ap.add_argument("--assertion", help="Expression inside klee_assert")
    ap.add_argument("--comment-lines", type=int, nargs='*', default=[], help="Line numbers to comment out")
    ap.add_argument("--stub-functions", nargs='*', default=[], help="Function names to stub with return 0")

    args = ap.parse_args()
    sg_root = Path("../stase_generated_last")
    target_path = sg_root / "instrumented_source" / args.target_src

    if not target_path.exists():
        print(f"[✗] Error: File not found: {target_path}")
        return

    ensure_backup(target_path)

    if args.assert_line and args.assertion:
        inject_assert(target_path, args.assert_line, args.assertion)

    if args.comment_lines:
        comment_out_lines(target_path, args.comment_lines)

    if args.stub_functions:
        stub_functions(target_path, args.stub_functions)

if __name__ == "__main__":
    main()

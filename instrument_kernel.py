#!/usr/bin/env python3
import argparse, shutil, re
from pathlib import Path
from setup_common import read_json, get_workspace, write

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-src", required=True, help="C file to insert the assertion into")
    parser.add_argument("--entry-src", required=True, help="C file that defines the entrypoint function")
    parser.add_argument("--assert-line", required=True, type=int)
    parser.add_argument("--assertion", required=True)
    parser.add_argument("--stub-functions", required=False, help="Optional JSON file with stubbed functions")
    parser.add_argument("--helper-files", nargs="*", default=[], help="Optional helper C files to preserve")
    parser.add_argument("--comment-lines", nargs="*", type=int, default=[], help="Lines to comment out instead of delete")
    return parser.parse_args()

def copy_preserved_files(original_src: Path, instrumented_src: Path, preserved: set):
    for rel_path in preserved:
        src_file = original_src / rel_path
        dst_file = instrumented_src / rel_path
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dst_file)
    print("[✓] Preserved files copied to instrumented_source")

def stub_out_irrelevant_sources(instrumented_src: Path, preserved_paths: set):
    for path in instrumented_src.rglob("*.c"):
        rel_path = str(path.relative_to(instrumented_src))
        if rel_path not in preserved_paths:
            path.write_text("/* stubbed out by instrument_kernel.py */\n")
    print("[✓] Stubbed irrelevant .c files in instrumented_source")

def stub_out_missing_headers(instrumented_src: Path):
    for path in instrumented_src.rglob("*.c"):
        content = path.read_text()
        includes = re.findall(r'#include\s+[<\"](.*?)[>\"]', content)
        for inc in includes:
            header_path = instrumented_src / inc
            if not header_path.exists():
                header_path.parent.mkdir(parents=True, exist_ok=True)
                header_path.write_text("/* stubbed header */\n")
    print("[✓] Stubbed missing headers in instrumented_source")

def write_kernel_stub_header(instrumented_src: Path):
    include_dir = instrumented_src / "include"
    include_dir.mkdir(parents=True, exist_ok=True)
    stub_code = """\n#ifndef __KERNEL_STUB_DEFS_H__
#define __KERNEL_STUB_DEFS_H__

#define pr_err(x...) do {} while (0)
#define pr_debug(x...) do {} while (0)
#define MODULE_LICENSE(x)
#define MODULE_AUTHOR(x)
#define MODULE_DESCRIPTION(x)
#define module_init(x)
#define module_exit(x)
#define __init
#define __exit

struct notifier_block {
    int (*notifier_call)(struct notifier_block *nb, unsigned long action, void *data);
};

static inline void make_dynamic_area() {}
static inline int is_executable(uint64_t x) { return 0; }
static inline int usb_register_notify(struct notifier_block *nb) { return 0; }
static inline void usb_unregister_notify(struct notifier_block *nb) {}

#endif
"""
    write(include_dir / "kernel_stub_defs.h", stub_code)
    print("[✓] Wrote instrumented_source/include/kernel_stub_defs.h")

def prepend_stub_header(file_path: Path):
    if not file_path.exists(): return
    lines = file_path.read_text().splitlines()
    include_line = '#include "include/kernel_stub_defs.h"'
    if include_line not in lines:
        lines.insert(0, include_line)
        file_path.write_text("\n".join(lines) + "\n")
        print(f"[✓] Inserted stub header in {file_path.name}")

def comment_out_lines(target_file: Path, line_nums: list):
    lines = target_file.read_text().splitlines()
    for i in line_nums:
        if 0 < i <= len(lines):
            lines[i - 1] = "// " + lines[i - 1]
    target_file.write_text("\n".join(lines) + "\n")
    print(f"[✓] Commented out lines: {line_nums} in {target_file.name}")

def comment_out_all_includes_except_stub(file: Path):
    lines = file.read_text().splitlines()
    new_lines = []
    for line in lines:
        if line.startswith("#include") and 'kernel_stub_defs.h' not in line:
            new_lines.append("// " + line)
        else:
            new_lines.append(line)
    file.write_text("\n".join(new_lines) + "\n")
    print(f"[✓] Commented out all includes except kernel_stub_defs.h in {file.name}")

def insert_assertion(target_file: Path, line_no: int, assertion: str):
    lines = target_file.read_text().splitlines()
    lines.insert(line_no - 1, assertion)
    target_file.write_text("\n".join(lines) + "\n")
    print(f"[✓] Inserted assertion at line {line_no} of {target_file.name}")

def inject_function_stubs(stub_file: Path, dest: Path):
    stubs = read_json(stub_file)
    code = "\n".join([f["stubbed function"] for f in stubs]) + "\n"
    write(dest / "driver_stubs.c", code)
    print("[✓] Wrote driver_stubs.c with function stubs")

def main():
    args = parse_args()
    ws = get_workspace()
    original_src = ws / "original_source"
    instrumented_src = ws / "instrumented_source"

    target_file = original_src / args.target_src
    entry_file = original_src / args.entry_src
    assert target_file.exists(), f"[✗] Target file not found: {target_file}"
    assert entry_file.exists(), f"[✗] Entry file not found: {entry_file}"

    preserved_paths = {args.target_src, args.entry_src, *args.helper_files}
    copy_preserved_files(original_src, instrumented_src, preserved_paths)
    write_kernel_stub_header(instrumented_src)

    for rel_path in preserved_paths:
        file = instrumented_src / rel_path
        if file.exists() and file.suffix == ".c":
            comment_out_all_includes_except_stub(file)
            prepend_stub_header(file)

    stubbed_target = instrumented_src / args.target_src
    if args.comment_lines:
        comment_out_lines(stubbed_target, args.comment_lines)
    insert_assertion(stubbed_target, args.assert_line, args.assertion)

    stub_out_irrelevant_sources(instrumented_src, preserved_paths)
    stub_out_missing_headers(instrumented_src)

    if args.stub_functions:
        inject_function_stubs(Path(args.stub_functions), ws)

if __name__ == "__main__":
    main()

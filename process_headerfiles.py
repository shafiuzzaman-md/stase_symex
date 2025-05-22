#!/usr/bin/env python3
import os
import re
import sys
from collections import defaultdict
from multiprocessing import Pool, cpu_count, Manager

INCLUDE_PATTERN = re.compile(r'^\s*#include\s+<(.+?)>')

def index_all_files(directories):
    file_index = defaultdict(list)
    for directory in directories:
        for root, _, files in os.walk(directory):
            for f in files:
                file_index[f].append(os.path.join(root, f))
    return dict(file_index)

def find_include_lines(file_path):
    matches = []
    try:
        with open(file_path, 'r') as f:
            for i, line in enumerate(f, 1):
                if INCLUDE_PATTERN.search(line):
                    matches.append((i, line.strip()))
    except:
        return []
    return matches

def replace_line(file_path, line_number, new_line):
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
        if lines[line_number - 1].strip() == new_line.strip():
            return False
        lines[line_number - 1] = new_line + '\n'
        with open(file_path, 'w') as f:
            f.writelines(lines)
        return True
    except:
        return False

def resolve_include(file_index, base_filename, include_dir):
    paths = file_index.get(base_filename, [])
    if not include_dir:
        return paths[0] if paths else None
    for p in paths:
        if os.path.basename(os.path.dirname(p)) == include_dir:
            return p
    return None

def process_single_file(args):
    file_path, file_index = args
    modified = False
    include_matches = find_include_lines(file_path)
    if not include_matches:
        return None

    rel_dir = os.path.dirname(file_path)
    output = [f"[Processing] {file_path}"]
    for line_number, line in include_matches:
        match = INCLUDE_PATTERN.search(line)
        if not match:
            continue

        full_path = match.group(1)
        base_filename = os.path.basename(full_path)
        include_dir = os.path.dirname(full_path)

        resolved = resolve_include(file_index, base_filename, include_dir)
        if resolved:
            rel_path = os.path.relpath(resolved, rel_dir).replace("\\", "/")
            success = replace_line(file_path, line_number, f'#include "{rel_path}"')
            if success:
                modified = True
                output.append(f"  → Line {line_number}: replaced with #include \"{rel_path}\"")
        else:
            output.append(f"  × Line {line_number}: could not resolve {full_path}")
    return "\n".join(output) if modified else None

def collect_c_and_h_files(directories):
    result = []
    for d in directories:
        for root, _, files in os.walk(d):
            for f in files:
                if f.endswith(('.c', '.h')):
                    result.append(os.path.join(root, f))
    return result

def main(target_dirs):
    print("[+] Indexing files...")
    file_index = index_all_files(target_dirs)
    print(f"[+] Indexed {sum(len(v) for v in file_index.values())} files.")

    print("[+] Collecting source files...")
    files_to_process = collect_c_and_h_files(target_dirs)
    print(f"[+] Found {len(files_to_process)} source files.")

    print("[+] Processing files in parallel...")
    with Pool(processes=cpu_count()) as pool:
        results = pool.map(process_single_file, [(f, file_index) for f in files_to_process])

    for res in results:
        if res:
            print(res)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 process_headerfiles.py <dir1> [dir2 ...]")
        sys.exit(1)

    main(sys.argv[1:])

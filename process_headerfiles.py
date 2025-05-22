#!/usr/bin/env python3
import os
import re
import sys
from collections import defaultdict

INCLUDE_PATTERN = re.compile(r'^\s*#include\s+<(.+?)>')

def index_files(directories):
    file_index = defaultdict(list)
    for directory in directories:
        for root, _, files in os.walk(directory):
            for file in files:
                file_index[file].append(os.path.join(root, file))
    return file_index

def resolve_include(file_index, base_filename, include_dir):
    candidates = file_index.get(base_filename, [])
    if not include_dir:
        return candidates[0] if candidates else None
    for path in candidates:
        if os.path.basename(os.path.dirname(path)) == include_dir:
            return path
    return None

def find_include_lines(file_path):
    matches = []
    try:
        with open(file_path, 'r') as f:
            for i, line in enumerate(f, 1):
                if INCLUDE_PATTERN.search(line):
                    matches.append((i, line.strip()))
    except Exception as e:
        print(f"[Error] Skipping {file_path}: {e}")
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
    except Exception as e:
        print(f"[Error] Could not update {file_path}: {e}")
        return False

def process_directories(directories):
    file_index = index_files(directories)
    print("[+] File index built.")

    for current_directory in directories:
        for root, _, files in os.walk(current_directory):
            for file in files:
                if not file.endswith((".c", ".h")):
                    continue

                file_path = os.path.join(root, file)
                include_matches = find_include_lines(file_path)

                if not include_matches:
                    continue

                print(f"\n[Processing] {file_path}")
                for line_number, line in include_matches:
                    match = INCLUDE_PATTERN.search(line)
                    if not match:
                        continue

                    full_path = match.group(1)
                    base_filename = os.path.basename(full_path)
                    include_dir = os.path.dirname(full_path)

                    resolved = resolve_include(file_index, base_filename, include_dir)
                    if resolved:
                        rel_path = os.path.relpath(resolved, os.path.dirname(file_path)).replace("\\", "/")
                        success = replace_line(file_path, line_number, f'#include "{rel_path}"')
                        if success:
                            print(f"  → Line {line_number}: replaced with #include \"{rel_path}\"")
                    else:
                        print(f"  × Line {line_number}: could not resolve {full_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 process_headerfiles.py <directory1> [directory2 ...]")
        sys.exit(1)

    target_dirs = sys.argv[1:]
    process_directories(target_dirs)

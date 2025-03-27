#!/usr/bin/env python3
import os
import re
import sys

def find_exact_file(directories, filename):
    for directory in directories:
        for root, dirs, files in os.walk(directory):
            if filename in files:
                return os.path.join(root, filename)
    return None

def find_exact_file_in_directory(directories, filename, target_directory):
    for directory in directories:
        for root, dirs, files in os.walk(directory):
            if filename in files and os.path.basename(root) == target_directory:
                return os.path.join(root, filename)
    return None

def find_pattern_in_file(file_path, pattern):
    with open(file_path, 'r') as file:
        lines = file.readlines()
    return [(line_number, line.strip()) for line_number, line in enumerate(lines, start=1) if re.search(pattern, line)]

def replace_line_with_exact_path(file_path, line_number, new_line):
    with open(file_path, 'r') as file:
        lines = file.readlines()
    lines[line_number - 1] = new_line + '\n'
    with open(file_path, 'w') as file:
        file.writelines(lines)

def process_directories(targets):
    pattern = r'^\s*#include\s+<(.+?)>'

    for current_directory in targets:
        for root, dirs, files in os.walk(current_directory):
            for file in files:
                if file.endswith((".c", ".h")):
                    file_path = os.path.join(root, file)
                    print(f"\n[Processing] {file_path}")
                    matches = find_pattern_in_file(file_path, pattern)

                    for line_number, line in matches:
                        match = re.search(pattern, line)
                        if not match:
                            continue

                        full_path = match.group(1)
                        base_filename = os.path.basename(full_path)
                        include_dir = os.path.dirname(full_path)

                        if include_dir:
                            resolved_path = find_exact_file_in_directory(targets, base_filename, include_dir)
                        else:
                            resolved_path = find_exact_file(targets, base_filename)

                        if resolved_path:
                            rel_path = os.path.relpath(resolved_path, os.path.dirname(file_path)).replace("\\", "/")
                            replace_line_with_exact_path(file_path, line_number, f'#include "{rel_path}"')
                            print(f"  → Line {line_number}: replaced with #include \"{rel_path}\"")
                        else:
                            print(f"  × Could not resolve: {full_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 process_headerfiles.py <directory1> [directory2 ...]")
        sys.exit(1)

    target_dirs = sys.argv[1:]
    process_directories(target_dirs)

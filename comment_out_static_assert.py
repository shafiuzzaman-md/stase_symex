#!/usr/bin/env python3
import os
import re
import sys

def comment_out_static_assert(file_path):
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()

        modified = False
        for i, line in enumerate(lines):
            if re.match(r'\s*STATIC_ASSERT', line):
                lines[i] = f'// {line.strip()}\n'
                modified = True

        if modified:
            with open(file_path, 'w') as file:
                file.writelines(lines)
            print(f"[✓] Commented STATIC_ASSERT in: {file_path}")
    except Exception as e:
        print(f"[!] Error processing {file_path}: {str(e)}")

def process_path(path):
    if os.path.isfile(path) and path.endswith((".h", ".c")):
        comment_out_static_assert(path)
    elif os.path.isdir(path):
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith((".h", ".c")):
                    comment_out_static_assert(os.path.join(root, file))
    else:
        print(f"[!] Skipping unsupported or non-existent path: {path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 comment_out_static_assert.py <file_or_directory> [more_files_or_directories...]")
        sys.exit(1)

    for path in sys.argv[1:]:
        process_path(path)

#!/usr/bin/env python3

import subprocess
import sys
import os
import shutil

OUTPUT_DIR = "../stase_generated"
INSTRUMENTED_SOURCE_DIR = os.path.join(OUTPUT_DIR, "instrumented_source")

def write_settings_file(clang_path, klee_path):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, "settings.py"), "w") as f:
        f.write(f'EDK2_PATH = "{os.path.abspath(INSTRUMENTED_SOURCE_DIR)}"\n')
        f.write(f'CLANG_PATH = "{clang_path}"\n')
        f.write(f'KLEE_PATH = "{klee_path}"\n')
    print(f"[+] settings.py created in {OUTPUT_DIR}/")

def validate_file(path, label):
    if not os.path.isfile(path):
        print(f"[!] Invalid {label} path: {path}")
        sys.exit(1)

def copy_source_tree(src):
    if os.path.exists(INSTRUMENTED_SOURCE_DIR):
        print(f"[!] Instrumented source already exists at {INSTRUMENTED_SOURCE_DIR}, removing...")
        shutil.rmtree(INSTRUMENTED_SOURCE_DIR)
    print(f"[+] Copying source from {src} to {INSTRUMENTED_SOURCE_DIR} ...")
    shutil.copytree(src, INSTRUMENTED_SOURCE_DIR, symlinks=True)
    print(f"[✓] Copied source to {INSTRUMENTED_SOURCE_DIR}")

def main():
    if len(sys.argv) != 4:
        print("Usage: python3 setup_ech.py <source-directory> <clang-path> <klee-path>")
        sys.exit(1)

    source_dir = sys.argv[1]
    clang_path = sys.argv[2]
    klee_path = sys.argv[3]

    if not os.path.isdir(source_dir):
        print(f"[!] Invalid source directory: {source_dir}")
        sys.exit(1)

    validate_file(clang_path, "Clang")
    validate_file(klee_path, "KLEE")

    copy_source_tree(source_dir)
    write_settings_file(clang_path, klee_path)

    print("[+] Rewriting #include <...> to #include \"...\"...")
    subprocess.run(["python3", "process_headerfiles.py", INSTRUMENTED_SOURCE_DIR, "--out-dir", OUTPUT_DIR], check=True)

    print("[+] Commenting out STATIC_ASSERT macros...")
    subprocess.run(["python3", "comment_out_static_assert.py", INSTRUMENTED_SOURCE_DIR, "--out-dir", OUTPUT_DIR], check=True)

    print("[+] Extracting GUIDs and global stubs...")
    subprocess.run(["python3", "extract_protocol_guids.py", INSTRUMENTED_SOURCE_DIR, "--out-dir", OUTPUT_DIR], check=True)

    print(f"[✓] Environment Configuration Harness (ECH) setup completed in {OUTPUT_DIR}/")

if __name__ == "__main__":
    main()

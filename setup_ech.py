#!/usr/bin/env python3

import subprocess
import sys
import os

def write_settings_file(edk2_dir, clang_path, klee_path, max_time=5):
    with open("settings.py", "w") as f:
        f.write(f'EDK2_PATH = "{os.path.abspath(edk2_dir)}"\n')
        f.write(f'CLANG_PATH = "{clang_path}"\n')
        f.write(f'KLEE_PATH = "{klee_path}"\n')
        f.write(f'MAX_KLEE_TIME = {max_time}\n')
    print("[+] settings.py created with EDK2, Clang, KLEE paths and MAX_KLEE_TIME.")

def validate_file(path, label):
    if not os.path.isfile(path):
        print(f"[!] Invalid {label} path: {path}")
        sys.exit(1)

def main():
    if len(sys.argv) < 4 or len(sys.argv) > 5:
        print("Usage: python3 setup_ech.py <edk2-directory> <clang-path> <klee-path> [max-klee-time]")
        sys.exit(1)

    edk2_dir = sys.argv[1]
    clang_path = sys.argv[2]
    klee_path = sys.argv[3]
    max_klee_time = int(sys.argv[4]) if len(sys.argv) == 5 else 5

    if not os.path.isdir(edk2_dir):
        print(f"[!] Invalid EDK2 directory: {edk2_dir}")
        sys.exit(1)

    validate_file(clang_path, "Clang")
    validate_file(klee_path, "KLEE")

    write_settings_file(edk2_dir, clang_path, klee_path, max_klee_time)

    print("[+] Rewriting #include <...> to #include \"...\"...")
    subprocess.run(["python3", "process_headerfiles.py", edk2_dir], check=True)

    print("[+] Commenting out STATIC_ASSERT macros...")
    subprocess.run(["python3", "comment_out_static_assert.py", edk2_dir], check=True)

    print("[+] Extracting GUIDs and global stubs...")
    subprocess.run(["python3", "extract_protocol_guids.py", edk2_dir], check=True)
    
    print("[✓] Environment Configuration Harness (ECH) setup completed successfully.")

if __name__ == "__main__":
    main()

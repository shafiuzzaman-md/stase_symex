#!/usr/bin/env python3

import subprocess
import sys
import os

def write_settings_file(edk2_dir, clang_path, klee_path):
    with open("settings.py", "w") as f:
        f.write(f'EDK2_PATH = "{os.path.abspath(edk2_dir)}"\n')
        f.write(f'CLANG_PATH = "{clang_path}"\n')
        f.write(f'KLEE_PATH = "{klee_path}"\n')
    print("[+] settings.py created.")

def main():
    if len(sys.argv) != 4:
        print("Usage: python3 setup_ech.py <edk2-directory> <clang-path> <klee-path>")
        sys.exit(1)

    edk2_path, clang_path, klee_path = sys.argv[1], sys.argv[2], sys.argv[3]

    if not os.path.isdir(edk2_path):
        print(f"[!] Provided path '{edk2_path}' is not a valid directory.")
        sys.exit(1)

    write_settings_file(edk2_path, clang_path, klee_path)

    print("[+] Running header file processor...")
    subprocess.run(["python3", "process_headerfiles.py", edk2_path], check=True)

    print("[+] Running static assert comment remover...")
    subprocess.run(["python3", "comment_out_static_assert.py", edk2_path], check=True)

    print("[✓] Environment Configuration Harness setup complete.")

if __name__ == "__main__":
    main()

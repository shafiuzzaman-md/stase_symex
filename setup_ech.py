#!/usr/bin/env python3

import subprocess
import sys
import os
import shutil

OUTPUT_DIR = "../stase_generated"
EDK2_COPY_DIR = os.path.join(OUTPUT_DIR, "edk2_copy")

def write_settings_file(clang_path, klee_path):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, "settings.py"), "w") as f:
        f.write(f'EDK2_PATH = "{os.path.abspath(EDK2_COPY_DIR)}"\n')
        f.write(f'CLANG_PATH = "{clang_path}"\n')
        f.write(f'KLEE_PATH = "{klee_path}"\n')
    print(f"[+] settings.py created in {OUTPUT_DIR}/")

def validate_file(path, label):
    if not os.path.isfile(path):
        print(f"[!] Invalid {label} path: {path}")
        sys.exit(1)

def copy_edk2_source(src):
    if os.path.exists(EDK2_COPY_DIR):
        print(f"[!] EDK2 copy already exists at {EDK2_COPY_DIR}, removing...")
        shutil.rmtree(EDK2_COPY_DIR)
    print(f"[+] Copying EDK2 source from {src} to {EDK2_COPY_DIR} ...")
    shutil.copytree(src, EDK2_COPY_DIR, symlinks=True)
    print(f"[✓] Copied EDK2 source to {EDK2_COPY_DIR}")

def main():
    if len(sys.argv) != 4:
        print("Usage: python3 setup_ech.py <edk2-directory> <clang-path> <klee-path>")
        sys.exit(1)

    edk2_dir = sys.argv[1]
    clang_path = sys.argv[2]
    klee_path = sys.argv[3]

    if not os.path.isdir(edk2_dir):
        print(f"[!] Invalid EDK2 directory: {edk2_dir}")
        sys.exit(1)

    validate_file(clang_path, "Clang")
    validate_file(klee_path, "KLEE")

    copy_edk2_source(edk2_dir)
    write_settings_file(clang_path, klee_path)

    print("[+] Rewriting #include <...> to #include \"...\"...")
    subprocess.run(["python3", "process_headerfiles.py", EDK2_COPY_DIR, "--out-dir", OUTPUT_DIR], check=True)

    print("[+] Commenting out STATIC_ASSERT macros...")
    subprocess.run(["python3", "comment_out_static_assert.py", EDK2_COPY_DIR, "--out-dir", OUTPUT_DIR], check=True)

    print("[+] Extracting GUIDs and global stubs...")
    subprocess.run(["python3", "extract_protocol_guids.py", EDK2_COPY_DIR, "--out-dir", OUTPUT_DIR], check=True)

    print(f"[✓] Environment Configuration Harness (ECH) setup completed in {OUTPUT_DIR}/")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import os
import shutil
import sys
from pathlib import Path
from setup_common import next_workspace

def emit_fake_libc(include_path):
    os.makedirs(include_path, exist_ok=True)
    with open(os.path.join(include_path, "string.h"), "w") as f:
        f.write("void *memcpy(void *, const void *, unsigned long);\n")
        f.write("int strcmp(const char *, const char *);\n")
    with open(os.path.join(include_path, "stdint.h"), "w") as f:
        f.write("typedef unsigned int uint32_t;\n")
        f.write("typedef unsigned long long uint64_t;\n")
    asm_path = os.path.join(include_path, "asm")
    os.makedirs(asm_path, exist_ok=True)
    with open(os.path.join(asm_path, "types.h"), "w") as f:
        f.write("typedef unsigned int u32;\n")
        f.write("typedef unsigned long long u64;\n")
    linux_path = os.path.join(include_path, "linux")
    os.makedirs(linux_path, exist_ok=True)
    with open(os.path.join(linux_path, "types.h"), "w") as f:
        f.write("typedef unsigned int u32;\n")
        f.write("typedef unsigned long long u64;\n")

def copy_kernel_source(src, dest):
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(src, dest, symlinks=True, ignore=shutil.ignore_patterns("*.o", "*.a", "*.so", "*.mod.*"))
    print(f"[✓] Kernel source copied successfully.")

def main():
    if len(sys.argv) != 2:
        print("Usage: setup_kernel_environment.py <kernel-src>")
        sys.exit(1)

    src_kernel = sys.argv[1]

    workspace = next_workspace()
    original = os.path.join(workspace, "original_source")

    print("[+] Copying kernel source...")
    print(f"[+] Copying from {src_kernel} to {original}")
    copy_kernel_source(src_kernel, original)

    print("[+] Emitting fake libc headers...")
    emit_fake_libc(os.path.join(original, "fake_libc_include"))

    print("[✓] Kernel environment setup complete.")

if __name__ == "__main__":
    main()

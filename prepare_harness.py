# prepare_harness.py

import subprocess
import sys
import os

if len(sys.argv) != 2:
    print("Usage: python3 prepare_harness.py <edk2-directory>")
    sys.exit(1)

edk2_path = sys.argv[1]

if not os.path.isdir(edk2_path):
    print(f"[!] Provided path '{edk2_path}' is not a valid directory.")
    sys.exit(1)

print("[+] Running header file processor...")
subprocess.run(["python3", "process_headerfiles.py", edk2_path], check=True)

print("[+] Running static assert comment remover...")
subprocess.run(["python3", "comment_out_static_assert.py", edk2_path], check=True)

print("[✓] Harness preparation completed.")

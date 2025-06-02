#!/usr/bin/env python3
import sys, subprocess, shutil
from pathlib import Path
from setup_common import next_workspace, validate_path, copy_source_tree

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 setup_edk2_environment.py <edk2-src>")
        sys.exit(1)

    src = Path(sys.argv[1])
    validate_path(src, "EDK2")

    ws = next_workspace()
    instr_src = ws / "instrumented_source"
    copy_source_tree(src, instr_src)

    helper = Path(__file__).with_name("uefi_helper_stubs.c")
    if helper.exists():
        shutil.copy(helper, ws / "uefi_helper_stubs.c")
        print("[✓] Copied uefi_helper_stubs.c")

    subprocess.run(["python3", "process_headerfiles.py", str(instr_src), "--out-dir", str(ws)], check=True)
    subprocess.run(["python3", "comment_out_static_assert.py", str(instr_src), "--out-dir", str(ws)], check=True)
    subprocess.run(["python3", "extract_protocol_guids.py", str(instr_src), "--out-dir", str(ws)], check=True)

    print(f"[✓] Setup completed in {ws}/")

if __name__ == "__main__":
    main()

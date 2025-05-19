#!/usr/bin/env python3
import subprocess, sys, os, shutil, pathlib, glob, re
from pathlib import Path 
# -------------------------------------------------------------------------
# rolling work-dir  stase_generated_<N>   +  alias  stase_generated_last
# -------------------------------------------------------------------------
def next_workspace(base="stase_generated"):
    """
    Return a fresh   ../stase_generated_<N>   directory and update
    ../stase_generated_last → <newdir> .  N is the first non-existing integer.
    """
    base_parent = pathlib.Path("..").resolve()

    n = 0
    while True:
        candidate = base_parent / f"{base}_{n}"
        if not candidate.exists():
            candidate.mkdir(parents=True)           # ← create the fresh one
            break
        n += 1                                      # otherwise try next number

    alias = base_parent / f"{base}_last"
    if alias.is_symlink() or alias.exists():
        alias.unlink()
    alias.symlink_to(candidate, target_is_directory=True)

    print(f"[+] Workspace  {candidate.name}  created  (alias {alias.name} updated)")
    return candidate


OUTPUT_DIR = str(next_workspace())
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
        print("Usage: python3 setup_edk2_environment.py <source-directory> <clang-path> <klee-path>")
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

    # ---- copy the EDK-specific helper stub into the workspace ------------
    helper_src = Path(__file__).with_name("uefi_helper_stubs.c")   # master copy
    helper_dst = Path(OUTPUT_DIR) / "uefi_helper_stubs.c"          # per-run copy
    if helper_src.exists():
        shutil.copy(helper_src, helper_dst)
        print(f"[✓] helper stub copied → {helper_dst.relative_to(Path(OUTPUT_DIR).parent)}")
    # ----------------------------------------------------------------------

    
    write_settings_file(clang_path, klee_path)

    print("[+] Rewriting #include <...> to #include \"...\"...")
    subprocess.run(["python3", "process_headerfiles.py", INSTRUMENTED_SOURCE_DIR, "--out-dir", OUTPUT_DIR], check=True)

    print("[+] Commenting out STATIC_ASSERT macros...")
    subprocess.run(["python3", "comment_out_static_assert.py", INSTRUMENTED_SOURCE_DIR, "--out-dir", OUTPUT_DIR], check=True)

    print("[+] Extracting GUIDs and global stubs...")
    subprocess.run(["python3", "extract_protocol_guids.py", INSTRUMENTED_SOURCE_DIR, "--out-dir", OUTPUT_DIR], check=True)

    print(f"[✓] Setup completed successfully in {OUTPUT_DIR}/.")

if __name__ == "__main__":
    main()

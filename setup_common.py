#!/usr/bin/env python3
import pathlib, re, sys, shutil, textwrap, os, json

def next_workspace(base="stase_generated"):
    """
    Return a fresh ../stase_generated_<N> directory and update
    ../stase_generated_last → <newdir>
    """
    base_parent = pathlib.Path("..").resolve()
    n = 0
    while True:
        candidate = base_parent / f"{base}_{n}"
        if not candidate.exists():
            candidate.mkdir(parents=True)
            break
        n += 1

    alias = base_parent / f"{base}_last"
    if alias.exists() or alias.is_symlink():
        alias.unlink()
    alias.symlink_to(candidate, target_is_directory=True)

    print(f"[+] Workspace {candidate.name} created (alias {alias.name} updated)")
    return candidate

def write_settings_py(output_dir, edk2_path, clang_path, klee_path):
    with open(pathlib.Path(output_dir) / "settings.py", "w") as f:
        f.write(f'EDK2_PATH = "{edk2_path}"\n')
        f.write(f'CLANG_PATH = "{clang_path}"\n')
        f.write(f'KLEE_PATH = "{klee_path}"\n')
    print("[✓] settings.py written")

def write_settings_json(output_dir, kernel_path, clang_path, klee_path):
    settings = {
        "KERNEL_PATH": str(kernel_path),
        "CLANG_PATH": str(clang_path),
        "KLEE_PATH": str(klee_path),
    }
    with open(pathlib.Path(output_dir) / "settings.json", "w") as f:
        json.dump(settings, f, indent=2)
    print("[✓] settings.json written")

def validate_path(p, label):
    if not pathlib.Path(p).exists():
        sys.exit(f"[✗] {label} not found: {p}")

def copy_source_tree(src, dest):
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(src, dest, symlinks=True)
    print(f"[✓] Copied source to {dest}")

def write(path: pathlib.Path, content: str):
    path.write_text(textwrap.dedent(content))


def read_json(path):
    with open(path, "r") as f:
        return json.load(f)

def get_workspace(base="stase_generated_last"):
    resolved = pathlib.Path("..").resolve() / base
    if not resolved.exists():
        sys.exit(f"[✗] Workspace not found: {resolved}")
    return resolved

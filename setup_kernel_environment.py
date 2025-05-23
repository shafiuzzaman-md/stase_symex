#!/usr/bin/env python3
"""
setup_kernel_environment.py  –  *thin* kernel workspace
────────────────────────────────────────────────────────
Creates a new   stase_generated_<n>/   directory that contains only:

    instrumented_source/           ← initially empty
    fake_libc_include/             ← fake libc + auto-stub bucket
    include/linux/fallback_macros.h
    settings.json                  ← absolute paths to kernel/clang/klee

The heavy lifting (copying the minimal set of sources and rewriting
angle-bracket #includes) happens later inside setup_driver.py.
"""

import json, os, pathlib, re, shutil, sys, textwrap

# ────────────────────────── helpers ──────────────────────────
WS_BASE   = pathlib.Path("..").resolve()        # parent of stase_symex
FAKE_DIR  = "fake_libc_include"

def next_workspace() -> pathlib.Path:
    patt = re.compile(r"^stase_generated_(\d+)$")
    n    = max((int(m.group(1)) for p in WS_BASE.iterdir()
                if (m := patt.match(p.name))), default=-1) + 1
    ws   = WS_BASE / f"stase_generated_{n}"
    ws.mkdir()
    alias = WS_BASE / "stase_generated_last"
    if alias.exists() or alias.is_symlink():
        alias.unlink()
    alias.symlink_to(ws, target_is_directory=True)
    print(f"[+] workspace  {ws.name}   (alias → {alias.name})")
    return ws

def write(p: pathlib.Path, s: str):
    p.write_text(textwrap.dedent(s))

def emit_fake_libc(root: pathlib.Path):
    fake = root / FAKE_DIR; fake.mkdir()
    # ––– a *very* small subset; extend when you miss something –––
    write(fake / "string.h", """
        #pragma once
        void *memcpy(void*,const void*,unsigned long);
        void *memset(void*,int,unsigned long);
    """)
    write(fake / "stdlib.h", """
        #pragma once
        void *malloc(unsigned long); void free(void*);
    """)
    # catch-all linux_types_stub.h (same as before, trimmed here)
    write(fake / "linux_types_stub.h", """
        #pragma once

        #define __linux_bool_defined

        typedef unsigned long __kernel_ulong_t;
        typedef __kernel_ulong_t __kernel_size_t;
        typedef __kernel_ulong_t __kernel_ssize_t;
        typedef unsigned int u32;
        typedef unsigned short u16;
        typedef unsigned char u8;

        typedef unsigned int __kernel_uid32_t;
        typedef unsigned int __kernel_gid32_t;
        typedef unsigned short __kernel_uid16_t;
        typedef unsigned short __kernel_gid16_t;

        typedef __kernel_ulong_t __kernel_mode_t;
        typedef __kernel_ulong_t __kernel_off_t;
        typedef __kernel_ulong_t __kernel_pid_t;
        typedef __kernel_ulong_t __kernel_daddr_t;
        typedef __kernel_ulong_t __kernel_key_t;
        typedef __kernel_ulong_t __kernel_suseconds_t;
        typedef __kernel_ulong_t __kernel_timer_t;
        typedef __kernel_ulong_t __kernel_clockid_t;
        typedef __kernel_ulong_t __kernel_mqd_t;

        typedef struct __kernel_fd_set { unsigned long fds_bits[16]; } __kernel_fd_set;
        typedef __kernel_fd_set fd_set;
        // Type aliases that are often missing
        typedef unsigned long __kernel_ulong_t;
        typedef __kernel_ulong_t __kernel_off_t;
        typedef __kernel_ulong_t __kernel_clockid_t;
        typedef __kernel_ulong_t __kernel_daddr_t;
        typedef __kernel_ulong_t __kernel_caddr_t;
        typedef __kernel_ulong_t __kernel_loff_t;
        typedef __kernel_ulong_t __kernel_ptrdiff_t;
        typedef __kernel_ulong_t __kernel_clock_t;

        // Explicitly define bitwise types to avoid parser errors
        #define __bitwise

        // Int types
        typedef unsigned char  u8;
        typedef unsigned short u16;
        typedef unsigned int   u32;
        typedef unsigned long  u64;
        typedef signed char    s8;
        typedef short          s16;
        typedef int            s32;
        typedef long           s64;
        typedef unsigned short __u16;
        typedef unsigned int __u32;
        typedef unsigned long long __u64;
        typedef short __s16;
        typedef int __s32;
        typedef long long __s64;
        
        #ifndef NULL
        #define NULL ((void*)0)
        #endif

        #ifndef true
        #define true 1
        #endif

        #ifndef false
        #define false 0
        #endif
        typedef __int128 __s128;
        typedef unsigned __int128 __u128;
        // atomic helpers
        #ifndef arch_atomic_read
        #define arch_atomic_read(v)         ((v)->counter)
        #endif

        #ifndef arch_atomic_set
        #define arch_atomic_set(v, i)       ((v)->counter = (i))
        #endif

        #ifndef arch_atomic_add
        #define arch_atomic_add(i, v)       ((v)->counter += (i))
        #endif

        #ifndef arch_atomic_sub
        #define arch_atomic_sub(i, v)       ((v)->counter -= (i))
        #endif

        #ifndef arch_atomic_and
        #define arch_atomic_and(i, v)       ((v)->counter &= (i))
        #endif

        #ifndef smp_mb__before_atomic
        #define smp_mb__before_atomic()
        #endif

        #ifndef smp_mb__after_atomic
        #define smp_mb__after_atomic()
        #endif

        #ifndef smp_store_release
        #define smp_store_release(p, v) (*(p) = (v))
        #endif

        #ifndef smp_load_acquire
        #define smp_load_acquire(p) (*(p))
        #endif
        
    """)
    # directory where process_headerfiles drops automatic empty stubs
    (fake / "_auto_stubs_").mkdir()
    print("[✓] fake libc emitted")
def stub_atomic_instrumented(ws: pathlib.Path):
    path = ws / "instrumented_source/include/linux/atomic/atomic-instrumented.h"
    path.parent.mkdir(parents=True, exist_ok=True)
    write(path, "#pragma once\n/* stubbed by STASE */\n")
    print("[✓] Stubbed atomic-instrumented.h")

def emit_atomic_stubs(root: pathlib.Path):
    fake = root / FAKE_DIR
    write(fake / "atomic_stubs.h", """
        #pragma once
    """)
    print("[✓] atomic_stubs.h emitted")

def inject_fallback_macros(root: pathlib.Path):
    dst = root / "include/linux/fallback_macros.h"
    dst.parent.mkdir(parents=True, exist_ok=True)
    write(dst, """
        #pragma once
        #define __always_inline inline
        #define __init  #define __exit
        struct lockdep_map{int d;};
        struct work_struct{int d;}; struct delayed_work{int d; struct work_struct w;};
        struct rcu_work{int d; struct work_struct w;};
        struct srcu_struct{struct lockdep_map dep_map; int dummy;};
        static inline void rcu_try_lock_acquire(void*){} static inline void rcu_lock_release(void*){}
    """)
    print("[✓] fallback_macros.h injected")

def stub_atomic_arch_fallback(ws: pathlib.Path):
    path = ws / "instrumented_source/include/linux/atomic/atomic-arch-fallback.h"
    path.parent.mkdir(parents=True, exist_ok=True)
    write(path, "#pragma once\n/* stubbed out by STASE */\n")
    print("[✓] Stubbed atomic-arch-fallback.h")
def emit_arch_spinlock_stub(root: pathlib.Path):
    path = root / FAKE_DIR / "arch"
    path.mkdir(parents=True, exist_ok=True)
    write(path / "spinlock_types_stub.h", """
        #pragma once
        typedef struct { int dummy; } arch_spinlock_t;
    """)
    print("[✓] arch_spinlock_t stub emitted")

# ─────────────────────────── main ────────────────────────────
def main():
    if len(sys.argv) != 4:
        sys.exit("usage: setup_kernel_environment.py <kernel-src> <clang-bin> <klee-bin>")

    kernel   = pathlib.Path(sys.argv[1]).resolve()
    clang    = pathlib.Path(sys.argv[2]).resolve()
    klee     = pathlib.Path(sys.argv[3]).resolve()

    for p,label in ((kernel,"kernel"),(clang,"clang"),(klee,"klee")):
        if not p.exists():
            sys.exit(f"{label} path not found: {p}")

    ws = next_workspace()
    (ws / "instrumented_source").mkdir()
    # Pre-create stubbed version of atomic-arch-fallback.h to prevent redefinition errors
    atomic_stub_path = ws / "instrumented_source/include/linux/atomic/atomic-arch-fallback.h"
    atomic_stub_path.parent.mkdir(parents=True, exist_ok=True)
    write(atomic_stub_path, "#pragma once\n/* stubbed out by STASE */\n")
    print("[✓] atomic-arch-fallback.h stubbed out")

    emit_fake_libc(ws)
    emit_atomic_stubs(ws)
    inject_fallback_macros(ws / "instrumented_source")
    stub_atomic_arch_fallback(ws)
    stub_atomic_instrumented(ws)

    # settings.json → consumed by setup_driver.py & run_analysis.py
    (ws / "settings.json").write_text(json.dumps({
        "KERNEL_PATH" : str(kernel),
        "CLANG_PATH"  : str(clang),
        "KLEE_PATH"   : str(klee)
    }, indent=2))
    print("[✓] workspace initialised – ready for setup_driver.py")

if __name__ == "__main__":
    main()

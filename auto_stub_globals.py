#!/usr/bin/env python3
import re
import sys
from pathlib import Path

STUB_FILE = "generated_klee_drivers/global_stubs.h"

def extract_missing_symbols(klee_log):
    with open(klee_log, 'r') as f:
        content = f.read()
    return set(re.findall(r"Unable to load symbol\((gEfi\w+)\)", content))

def append_stub_declarations(symbols):
    Path(STUB_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(STUB_FILE, 'a') as f:
        for symbol in symbols:
            f.write(f"EFI_GUID {{symbol}};\n")
    print(f"[+] Added {{len(symbols)}} stub(s) to {{STUB_FILE}}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 auto_stub_globals.py <klee_output.log>")
        sys.exit(1)

    missing = extract_missing_symbols(sys.argv[1])
    if not missing:
        print("[-] No missing symbols found.")
        sys.exit(0)

    append_stub_declarations(missing)

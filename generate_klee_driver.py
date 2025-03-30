#!/usr/bin/env python3

import os
import argparse

def get_header_if_exists(source_file, output_dir):
    base, _ = os.path.splitext(source_file)
    header_file = f"{base}.h"
    if os.path.exists(header_file):
        header_rel = os.path.relpath(header_file, output_dir)
        return f'#include "{header_rel}"'
    return ""

def generate_klee_driver(entrypoint, source_file, output_name=None):
    out_dir = "generated_klee_drivers"
    os.makedirs(out_dir, exist_ok=True)

    header_line = get_header_if_exists(source_file, out_dir)
    source_include = f'#include "{os.path.relpath(source_file, out_dir)}"'
    out_file = os.path.join(out_dir, output_name or f'klee_driver_{entrypoint}.c')

    # Driver content with symbolic gImageHandle, gST, buffer + gSmst stub
    code = f"""// Auto-generated KLEE driver for {entrypoint}
#include "global_stubs.h"
#include "global_stub_defs.c"
#include "../klee/klee.h"
#include <string.h>
#include <stdlib.h>
{header_line}
{source_include}

// Stub function to simulate gSmst->SmmAllocatePool
EFI_STATUS EFIAPI DummyAllocatePool(
    IN EFI_MEMORY_TYPE PoolType,
    IN UINTN Size,
    OUT VOID **Buffer
) {{
    *Buffer = malloc(Size);
    klee_make_symbolic(*Buffer, Size, "SmmPoolBuffer");
    return EFI_SUCCESS;
}}

EFI_STATUS EFIAPI DummyInstallProtocolInterface(
    EFI_HANDLE *Handle,
    EFI_GUID *Protocol,
    EFI_INTERFACE_TYPE InterfaceType,
    VOID *Interface
) {{
    return EFI_SUCCESS;
}}

int main() {{
    // Stub initialization
    static EFI_SMM_SYSTEM_TABLE2 gSmstStub;
    gSmstStub.SmmAllocatePool = DummyAllocatePool;
    gSmstStub.SmmInstallProtocolInterface = DummyInstallProtocolInterface;
    gSmst = &gSmstStub;

    // Symbolic system table and image handle
    klee_make_symbolic(&gImageHandle, sizeof(gImageHandle), "gImageHandle");
    static EFI_SYSTEM_TABLE SystemTable;
    klee_make_symbolic(&SystemTable, sizeof(SystemTable), "SystemTable");
    gST = &SystemTable;

    // Directed symbolic execution for line 146 (OOB_WRITE)
    uint8_t *OutputBuffer[1];
    uint8_t InnerBuf[4];  // small to trigger OOB
    klee_make_symbolic(InnerBuf, sizeof(InnerBuf), "InnerBuf");
    OutputBuffer[0] = InnerBuf;

    {entrypoint}(gImageHandle, gST);

    return 0;
}}
"""

    with open(out_file, "w") as f:
        f.write(code)

    print(f"[+] KLEE driver generated at: {out_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a KLEE driver for an entrypoint.")
    parser.add_argument("entrypoint", help="Entrypoint function (e.g., FooEntryPoint)")
    parser.add_argument("source_file", help="Path to source file (e.g., ../edk2-testcases/Foo.c)")
    parser.add_argument("--output", help="Optional output filename")
    args = parser.parse_args()

    generate_klee_driver(args.entrypoint, args.source_file, args.output)

#!/usr/bin/env python3
import os
import argparse

def get_header_from_source(source_file, output_dir):
    source_abs = os.path.abspath(source_file)
    output_abs = os.path.abspath(output_dir)
    rel_path = os.path.relpath(source_abs, output_abs)
    header_path = rel_path.replace(".c", ".h")
    return f'#include "{header_path}"'

def find_edk_root(path):
    if os.path.isfile(path):
        path = os.path.dirname(path)
    path = os.path.abspath(path)
    while path != "/" and not any(name.lower().startswith("mdepkg") for name in os.listdir(path)):
        path = os.path.dirname(path)
    return path

def generate_klee_driver(entrypoint, source_file, output_name=None):
    out_dir = "generated_klee_drivers"
    os.makedirs(out_dir, exist_ok=True)
    header_line = get_header_from_source(source_file, out_dir)
    output_name = output_name or f'klee_driver_{entrypoint}.c'
    out_path = os.path.join(out_dir, output_name)

    edk_path = find_edk_root(source_file)
    if not edk_path or not os.path.isdir(edk_path):
        print(f"[!] Could not locate EDK2 root for: {source_file}")
        return

    edk_path = os.path.relpath(edk_path, out_dir)

    code = f"""\n#define __PI_SMM_DRIVER__ 1
#include "{edk_path}/MdePkg/Include/Base.h"
#include "{edk_path}/MdePkg/Include/Uefi/UefiBaseType.h"
#include "{edk_path}/MdePkg/Include/Uefi/UefiSpec.h"
#include "{edk_path}/MdePkg/Include/Pi/PiSmmCis.h"
#include "{edk_path}/MdePkg/Include/Protocol/SmmBase2.h"
#include "{edk_path}/MdePkg/Include/Library/SmmServicesTableLib.h"

#include "{edk_path}/MdePkg/Include/Uefi/UefiMultiPhase.h"
#include "{edk_path}/BaseTools/Source/C/Include/Common/PiFirmwareVolume.h"
#include "{edk_path}/MdeModulePkg/Include/Protocol/FaultTolerantWrite.h"
#include "{edk_path}/MdePkg/Include/Protocol/DriverBinding.h"
#include "{edk_path}/MdePkg/Include/Protocol/ComponentName.h"
#include "{edk_path}/MdePkg/Include/Protocol/ComponentName2.h"
#include "{edk_path}/MdePkg/Include/IndustryStandard/Pci22.h"
#include "{edk_path}/MdePkg/Include/Library/BaseLib.h"
#include "{edk_path}/BaseTools/Source/C/Include/Protocol/GraphicsOutput.h"
#include "{edk_path}/MdeModulePkg/Bus/Pci/PciBusDxe/PciBus.h"
#include "{edk_path}/MdePkg/Library/SmmMemLib/SmmMemLib.c"
#include "{edk_path}/MdePkg/Library/BaseMemoryLib/CopyMemWrapper.c"
#include "{edk_path}/MdePkg/Library/BaseMemoryLib/CopyMem.c"
#include "{edk_path}/MdePkg/Library/BaseLib/Math64.c"
#include "{edk_path}/MdePkg/Library/BaseLib/DivU64x32.c"
#include "{edk_path}/StandaloneMmPkg/Library/StandaloneMmMemLib/StandaloneMmMemLib.c"
#include "{edk_path}/MdeModulePkg/Library/SmmLockBoxLib/SmmLockBoxDxeLib.c"
#include "{edk_path}/MdeModulePkg/Universal/Variable/RuntimeDxe/VariableRuntimeCache.c"
#include "{edk_path}/MdeModulePkg/Universal/Variable/RuntimeDxe/TcgMorLockSmm.c"
#include "{edk_path}/MdeModulePkg/Include/Protocol/SmmVariable.h"

#include "../klee/klee.h"
#include <string.h>
#include <stdlib.h>
{header_line}

// Stubbed EFI System Table and Image Handle
EFI_SYSTEM_TABLE gSysTable;
EFI_HANDLE gImageHandle = (EFI_HANDLE)0;

// Stubbed Driver Services Table
EFI_DXE_SERVICES *gDS = NULL;
EFI_BOOT_SERVICES *gBS = NULL;
EFI_RUNTIME_SERVICES *gRT = NULL;
EFI_SYSTEM_TABLE *gST = NULL;


VOID *EFIAPI ZeroMem(VOID *Buffer, UINTN Size) {{
    return memset(Buffer, 0, Size);
}}

VOID *EFIAPI AllocateZeroPool(IN UINTN Size) {{
    void *ptr = malloc(Size);
    if (ptr) ZeroMem(ptr, Size);
    return ptr;
}}

UINTN EFIAPI AsciiStrSize(IN CONST CHAR8 *String) {{
    return (String == NULL) ? 0 : strlen(String) + 1;
}}

INTN EFIAPI AsciiStrCmp(IN CONST CHAR8 *FirstString, IN CONST CHAR8 *SecondString) {{
    return strcmp(FirstString, SecondString);
}}

EFI_STATUS EFIAPI AsciiStrCpyS(CHAR8 *Dest, UINTN DestSize, CONST CHAR8 *Src) {{
    strncpy(Dest, Src, DestSize);
    return EFI_SUCCESS;
}}

EFI_STATUS EFIAPI MySmmAllocatePool(
    IN EFI_MEMORY_TYPE PoolType,
    IN UINTN Size,
    OUT VOID **Buffer
) {{
    if (!Buffer) return EFI_INVALID_PARAMETER;
    *Buffer = malloc(Size);
    if (!*Buffer) return EFI_OUT_OF_RESOURCES;
    ZeroMem(*Buffer, Size);
    return EFI_SUCCESS;
}}

EFI_SMM_SYSTEM_TABLE2 gSmstMock = {{
    .SmmAllocatePool = MySmmAllocatePool,
    .SmmInstallProtocolInterface = NULL
}};

EFI_SMM_SYSTEM_TABLE2 *gSmst = &gSmstMock;

int main() {{
    {entrypoint}(gImageHandle, &gSysTable);
    return 0;
}}
"""

    with open(out_path, "w") as f:
        f.write(code)

    print(f"[+] KLEE driver generated at: {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a KLEE driver from entrypoint and source file.")
    parser.add_argument("entrypoint", help="Entrypoint function (e.g., CharConverterEntryPoint)")
    parser.add_argument("source_file", help="Path to source file (e.g., ../edk2-testcases/Testcases/...)")
    parser.add_argument("--output", help="Optional output filename")
    args = parser.parse_args()

    generate_klee_driver(args.entrypoint, args.source_file, args.output)

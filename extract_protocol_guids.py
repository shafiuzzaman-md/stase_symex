#!/usr/bin/env python3

import os
import re
import sys

GUID_PATTERN = re.compile(r'\b(g[A-Z][A-Za-z0-9_]*Guid)\b')
GLOBAL_VAR_PATTERN = re.compile(
    r'\b((?:EFI|CHAR|UINT|BOOLEAN|LIST|VARIABLE|VOID)[_A-Z0-9a-z \*\[\]]+)\s+(g[A-Z][A-Za-z0-9_]*|m[A-Z][A-Za-z0-9_]*)\s*;',
    re.MULTILINE
)

# Types to reject or avoid
TYPE_BLACKLIST = re.compile(r'\b(return|STATIC|delete|UNKNOWN|CVfr|ENV_VAR_LIST|SHELL_MAP_LIST|PLD_|FWB_|FV_|OPTIONS|COMPILER_RUN_STATUS|USB_CLASS_FORMAT|ACPI_BOARD_INFO|EFI_ISCSI_|EFI_AUTHENTICATION_INFO|EFI_QUESION_TYPE|EFI_TLS|EFI_MM_|EFI_DHCP6_PROTOCOL|EFI_VARSTORE_INFO|EFI_TCP|EFI_IP4_PROTOCOL|EFI_VFR_|EFI_VFR_VARSTORE_TYPE|EFI_SERVICE_BINDING_PROTOCOL)\b')

# Types we know exist
TYPE_WHITELIST = {
    "EFI_GUID", "EFI_HANDLE", "EFI_SYSTEM_TABLE", "EFI_BOOT_SERVICES", "EFI_RUNTIME_SERVICES",
    "CHAR16", "BOOLEAN", "UINT8", "UINT16", "UINT32", "UINT64", "LIST_ENTRY", "VOID*"
}

COMMON_INCLUDES = [
    "MdePkg/Include/Base.h",
    "MdePkg/Include/Uefi/UefiBaseType.h",
    "MdePkg/Include/Uefi/UefiSpec.h",
    "MdePkg/Include/Pi/PiSmmCis.h",
    "MdePkg/Include/Protocol/SmmBase2.h",
    "MdePkg/Include/Library/SmmServicesTableLib.h",
    "MdePkg/Include/Uefi/UefiMultiPhase.h",
    "BaseTools/Source/C/Include/Common/PiFirmwareVolume.h",
    "MdeModulePkg/Include/Protocol/FaultTolerantWrite.h",
    "MdePkg/Include/Protocol/DriverBinding.h",
    "MdePkg/Include/Protocol/ComponentName.h",
    "MdePkg/Include/Protocol/ComponentName2.h",
    "MdePkg/Include/IndustryStandard/Pci22.h",
    "MdePkg/Include/Library/BaseLib.h",
    "BaseTools/Source/C/Include/Protocol/GraphicsOutput.h",
    "MdeModulePkg/Bus/Pci/PciBusDxe/PciBus.h",
    "MdePkg/Library/SmmMemLib/SmmMemLib.c",
    "MdePkg/Library/BaseMemoryLib/CopyMemWrapper.c",
    "MdePkg/Library/BaseMemoryLib/CopyMem.c",
    "MdePkg/Library/BaseLib/Math64.c",
    "MdePkg/Library/BaseLib/DivU64x32.c",
    "StandaloneMmPkg/Library/StandaloneMmMemLib/StandaloneMmMemLib.c",
    "MdeModulePkg/Library/SmmLockBoxLib/SmmLockBoxDxeLib.c",
    "MdeModulePkg/Universal/Variable/RuntimeDxe/VariableRuntimeCache.c",
    "MdeModulePkg/Universal/Variable/RuntimeDxe/TcgMorLockSmm.c",
    "MdeModulePkg/Include/Protocol/SmmVariable.h",
]

def is_valid_type(type_str):
    if TYPE_BLACKLIST.search(type_str):
        return False
    for allowed in TYPE_WHITELIST:
        if allowed in type_str:
            return True
    return False

def extract_symbols_from_edk2(edk2_dir):
    guids = set()
    globals = {}

    print("[+] Extracting GUIDs and global stubs...")
    for root, _, files in os.walk(edk2_dir):
        for fname in files:
            if not fname.endswith((".c", ".h")):
                continue
            path = os.path.join(root, fname)
            print(f"[*] Scanning: {path}")
            try:
                with open(path, encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    guids.update(GUID_PATTERN.findall(content))
                    for match in GLOBAL_VAR_PATTERN.findall(content):
                        decl_type, name = match
                        decl_type = decl_type.strip()
                        if is_valid_type(decl_type):
                            globals[name] = decl_type
            except Exception as e:
                print(f"[!] Failed to process {path}: {e}")
    return sorted(guids), globals
def write_stubs(edk2_dir, header_path="generated_klee_drivers/global_stubs.h", def_path="generated_klee_drivers/global_stub_defs.c"):
    os.makedirs(os.path.dirname(header_path), exist_ok=True)

    guids, globals = extract_symbols_from_edk2(edk2_dir)

    # ✅ Ensure essential UEFI globals are always defined
    essential_globals = {
        "gDS": "EFI_DXE_SERVICES *",
        "gBS": "EFI_BOOT_SERVICES *",
        "gRT": "EFI_RUNTIME_SERVICES *",
        "gST": "EFI_SYSTEM_TABLE *",
        "gImageHandle": "EFI_HANDLE"
    }
    for name, typ in essential_globals.items():
        globals.setdefault(name, typ)

    with open(header_path, "w") as h:
        h.write("// Auto-generated global stub declarations\n")
        h.write("#ifndef __GLOBAL_STUBS_H__\n#define __GLOBAL_STUBS_H__\n\n")
        h.write('#include <Uefi.h>\n#include <Library/UefiLib.h>\n\n')

        for g in guids:
            h.write(f"extern EFI_GUID {g};\n")

        h.write("\n// Global variable stubs\n")
        for name, decl_type in globals.items():
            h.write(f"extern {decl_type} {name};\n")

        h.write("\n#endif // __GLOBAL_STUBS_H__\n")

    with open(def_path, "w") as d:
        d.write("// Auto-generated global stub definitions\n")
        d.write('#include "global_stubs.h"\n\n')
        for name, decl_type in globals.items():
            init = " = 0" if "*" not in decl_type else " = NULL"
            d.write(f"{decl_type} {name}{init};\n")

        for g in guids:
            d.write(f"EFI_GUID {g} = {{0}};\n")

    print(f"[✓] Wrote {header_path} and {def_path} with {len(guids)} GUIDs and {len(globals)} globals.")

    os.makedirs(os.path.dirname(header_path), exist_ok=True)

    guids, globals = extract_symbols_from_edk2(edk2_dir)
    
    with open(header_path, "w") as h:
        h.write("// Auto-generated global stub declarations\n")
        h.write("#ifndef __GLOBAL_STUBS_H__\n#define __GLOBAL_STUBS_H__\n\n")
        for inc in COMMON_INCLUDES:
            full = os.path.normpath(os.path.join(edk2_dir, inc))
            rel = os.path.relpath(full, os.path.dirname(header_path))
            h.write(f'#include "{rel}"\n')
        h.write("\n")

        h.write("// GUID declarations\n")
        for g in guids:
            h.write(f"extern EFI_GUID {g};\n")

        h.write("\n// Global variable stubs\n")
        for name, decl_type in globals.items():
            h.write(f"extern {decl_type} {name};\n")

        h.write("\n#endif // __GLOBAL_STUBS_H__\n")

    with open(def_path, "w") as d:
        d.write("// Auto-generated global stub definitions\n")
        d.write('#include "global_stubs.h"\n\n')
        for name, decl_type in globals.items():
            init = " = 0" if "*" not in decl_type else " = NULL"
            d.write(f"{decl_type} {name}{init};\n")
        for g in guids:
            d.write(f"EFI_GUID {g} = {{0}};\n")

    print(f"[✓] Wrote {header_path} and {def_path} with {len(guids)} GUIDs and {len(globals)} globals.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 extract_protocol_guids.py <edk2-root-dir>")
        sys.exit(1)
    write_stubs(sys.argv[1])

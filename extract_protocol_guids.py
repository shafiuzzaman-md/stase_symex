#!/usr/bin/env python3

import os
import re
import sys
import yaml
import argparse

GUID_PATTERN = re.compile(r'\b(g[A-Z][A-Za-z0-9_]*Guid)\b')
GLOBAL_VAR_PATTERN = re.compile(
    r'\b((?:EFI|CHAR|UINT|BOOLEAN|LIST|VARIABLE|VOID)[_A-Z0-9a-z \*\[\]]+)\s+(g[A-Z][A-Za-z0-9_]*|m[A-Z][A-Za-z0-9_]*)\s*;',
    re.MULTILINE
)

TYPE_BLACKLIST = re.compile(
    r'\b(return|STATIC|delete|UNKNOWN|CVfr|ENV_VAR_LIST|SHELL_MAP_LIST|PLD_|FWB_|FV_|OPTIONS|COMPILER_RUN_STATUS|'
    r'USB_CLASS_FORMAT|ACPI_BOARD_INFO|EFI_ISCSI_|EFI_AUTHENTICATION_INFO|EFI_QUESION_TYPE|EFI_TLS|EFI_MM_|'
    r'EFI_DHCP6_PROTOCOL|EFI_VARSTORE_INFO|EFI_TCP|EFI_IP4_PROTOCOL|EFI_VFR_|EFI_VFR_VARSTORE_TYPE|'
    r'EFI_SERVICE_BINDING_PROTOCOL)\b'
)

TYPE_WHITELIST = {
    "EFI_GUID", "EFI_HANDLE", "EFI_SYSTEM_TABLE", "EFI_BOOT_SERVICES", "EFI_RUNTIME_SERVICES",
    "CHAR16", "BOOLEAN", "UINT8", "UINT16", "UINT32", "UINT64", "LIST_ENTRY", "VOID*"
}

SKIP_GLOBAL_DEFINITIONS = {
    "mSmmMemLibInternalMaximumSupportAddress",
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

def load_manual_definitions(path="manual_globals.yaml"):
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        data = yaml.safe_load(f)
        return data.get("manual_globals", {})

def is_valid_type(type_str):
    if TYPE_BLACKLIST.search(type_str):
        return False
    return any(allowed in type_str for allowed in TYPE_WHITELIST)

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

                    guids.update(set(g.strip() for g in GUID_PATTERN.findall(content)))

                    for decl_type, name in GLOBAL_VAR_PATTERN.findall(content):
                        decl_type = ' '.join(decl_type.strip().split())
                        if is_valid_type(decl_type) and name not in globals:
                            globals[name] = decl_type
            except Exception as e:
                print(f"[!] Failed to process {path}: {e}")

    manual_defs = load_manual_definitions()
    for k, v in manual_defs.items():
        if k not in globals:
            globals[k] = v.split()[0] + ' ' + ' '.join(v.split()[1:-2])

    return sorted(guids), globals, manual_defs

def write_stubs(edk2_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    header_path = os.path.join(out_dir, "global_stubs.h")
    def_path = os.path.join(out_dir, "global_stub_defs.c")

    guids, globals, manual_defs = extract_symbols_from_edk2(edk2_dir)

    with open(header_path, "w") as h:
        h.write("// Auto-generated global stub declarations\n")
        h.write("#ifndef __GLOBAL_STUBS_H__\n#define __GLOBAL_STUBS_H__\n\n")
        for inc in COMMON_INCLUDES:
            rel = os.path.relpath(os.path.join(edk2_dir, inc), os.path.dirname(header_path))
            h.write(f'#include "{rel}"\n')
        h.write("\n// GUID declarations\n")
        for g in sorted(set(guids)):
            h.write(f"extern EFI_GUID {g};\n")
        h.write("\n// Global variable stubs\n")
        for name, decl_type in globals.items():
            clean_type = decl_type.strip()
            if name in clean_type:
                clean_type = clean_type.replace(name, '').strip()
            h.write(f"extern {clean_type} {name};\n")
        h.write("\n#endif // __GLOBAL_STUBS_H__\n")

    with open(def_path, "w") as d:
        d.write("// Auto-generated global stub definitions\n")
        d.write(f'#include "{os.path.basename(header_path)}"\n\n')

        STRUCT_LIKE_TYPES = {
            "EFI_GUID", "LIST_ENTRY", "EFI_SYSTEM_TABLE", "EFI_BOOT_SERVICES", "EFI_RUNTIME_SERVICES"
        }

        for line in manual_defs.values():
            d.write(line + "\n")

        for name, decl_type in globals.items():
            if name in manual_defs or name in SKIP_GLOBAL_DEFINITIONS:
                print(f"[!] Skipping manual or duplicate global: {name}")
                continue

            clean_type = decl_type.replace("extern", "").strip()
            if name in clean_type:
                clean_type = clean_type.replace(name, '').strip()

            if any(t in clean_type for t in STRUCT_LIKE_TYPES):
                init = " = {0}"
            elif "*" in clean_type:
                init = " = NULL"
            else:
                init = " = 0"
            d.write(f"{clean_type} {name}{init};\n")

        written_guids = set()
        for g in sorted(guids):
            if g not in written_guids:
                d.write(f"EFI_GUID {g} = {{0}};\n")
                written_guids.add(g)

    print(f"[✓] Wrote {header_path} and {def_path} with {len(written_guids)} GUIDs and {len(globals)} globals.")

def deduplicate_file(file_path):
    seen = set()
    with open(file_path, 'r') as f:
        lines = f.readlines()

    with open(file_path, 'w') as f:
        for line in lines:
            stripped = line.strip()
            if stripped and stripped not in seen:
                f.write(line)
                seen.add(stripped)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("edk2_root_dir")
    parser.add_argument("--out-dir", default="generated_klee_drivers")
    args = parser.parse_args()

    write_stubs(args.edk2_root_dir, args.out_dir)
    deduplicate_file(os.path.join(args.out_dir, "global_stubs.h"))
    deduplicate_file(os.path.join(args.out_dir, "global_stub_defs.c"))

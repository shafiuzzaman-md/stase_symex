#!/usr/bin/env python3

import os
import re
import argparse

def parse_instruction(instr_line):
    """
    Parse a C-style array access and assignment like:
      (*OutputBuffer)[i] = (CHAR16)InputBuffer[i];
      (*OutputBuffer)[OutIndex++] = 0x1B;
    """
    instr_line = instr_line.strip().rstrip(';')

    # Case 1: (*OutputBuffer)[OutIndex++] = ...;
    pattern_esc = r"\(\*(\w+)\)\[(\w+)\+\+\]\s*=\s*.+"
    match_esc = re.match(pattern_esc, instr_line)
    if match_esc:
        buffer_ptr = match_esc.group(1)
        index_var = match_esc.group(2)
        return index_var, "*OutputSize", "1", "ESC_BLOCK"

    # Case 2: (*OutputBuffer)[i] = (CHAR16)InputBuffer[i];
    pattern_basic = r"\(\*(\w+)\)\[(\w+)\]\s*=\s*\((\w+)\)"
    match_basic = re.match(pattern_basic, instr_line)
    if match_basic:
        buffer_ptr = match_basic.group(1)
        index_var = match_basic.group(2)
        element_type = match_basic.group(3)
        return index_var, "*OutputSize", f"sizeof({element_type})", "NORMAL"

    raise ValueError("Unsupported instruction format: " + instr_line)


def generate_oob_snippet(index_var, allocated_size, element_size, instruction, mode):
    """
    Generate the KLEE OOB assertion and the original instruction.
    """
    if mode == "ESC_BLOCK":
        return (
            "// [OOB_WRITE] Auto-inserted assertion for multi-byte ESC sequence\n"
            f"klee_assert({index_var} + 4 <= {allocated_size}); // Prevents overflow from 4-byte write\n"
            f"{instruction}\n"
        )
    else:
        return (
            "// [OOB_WRITE] Auto-inserted assertion\n"
            f"klee_assert({index_var} < ({allocated_size} / {element_size})); // OOB check\n"
            f"{instruction}\n"
        )


def insert_assertion(source_file, line_number, vuln_name, instruction):
    if vuln_name != "OOB_WRITE":
        raise ValueError(f"Unsupported vulnerability type: {vuln_name}")

    # Parse the affected instruction
    try:
        index_var, alloc_size, elem_size, mode = parse_instruction(instruction)
    except ValueError as e:
        return str(e)

    snippet = generate_oob_snippet(index_var, alloc_size, elem_size, instruction, mode)

    if not os.path.isfile(source_file):
        return f"[ERROR] Source file '{source_file}' does not exist."

    with open(source_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    insert_index = line_number - 1
    if insert_index < 0 or insert_index > len(lines):
        return f"[ERROR] line_number {line_number} is invalid for file with {len(lines)} lines."

    # Avoid duplicate insertion
    if "// [OOB_WRITE]" in lines[insert_index - 1]:
        return f"[!] Assertion already present at line {line_number}, skipping."

    lines.insert(insert_index, snippet)

    source_dir = os.path.dirname(source_file)
    base_name = os.path.basename(source_file)
    name_part, ext_part = os.path.splitext(base_name)
    out_filename = f"{name_part}_{line_number}_{vuln_name}.c"
    out_path = os.path.join(source_dir, out_filename)

    with open(out_path, "w", encoding="utf-8") as out_f:
        out_f.writelines(lines)

    return f"[+] Inserted assertion at line {line_number} into '{out_path}'."


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Insert KLEE OOB assertion before a line in source code.")
    parser.add_argument("source_file", help="C source file to modify.")
    parser.add_argument("line_number", type=int, help="1-based line number to insert before.")
    parser.add_argument("vuln_type", help="Type of vulnerability. Supported: OOB_WRITE.")
    parser.add_argument("instruction", help="Instruction on that line (for parsing).")

    args = parser.parse_args()

    result = insert_assertion(
        args.source_file,
        args.line_number,
        args.vuln_type,
        args.instruction
    )

    print(result)

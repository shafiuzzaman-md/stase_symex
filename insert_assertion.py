#!/usr/bin/env python3

import os
import re

# Enhanced version of the insert_oob_assertion script that:
# - Takes source file, line number, vulnerability name, and instruction
# - Parses the instruction to extract index variable, element type, and generate the full assertion
# - Inserts assertion + original instruction before the target line
# - Writes the instrumented file to 'instrumented_code/'

def parse_instruction(instr_line):
    """
    Parse a C-style array access and assignment like:
      (*OutputBuffer)[i] = (CHAR16)InputBuffer[i];

    Returns:
      index_var, allocated_size_expr, element_size_expr
    """
    instr_line = instr_line.strip().rstrip(';')

    pattern = r"\(\*(\w+)\)\[(\w+)\]\s*=\s*\((\w+)\)"
    match = re.match(pattern, instr_line)
    if not match:
        raise ValueError("Unsupported instruction format: " + instr_line)

    buffer_ptr = match.group(1)         # OutputBuffer
    index_var = match.group(2)          # i
    element_type = match.group(3)       # CHAR16

    allocated_size_expr = f"*OutputSize"
    element_size_expr = f"sizeof({element_type})"

    return index_var, allocated_size_expr, element_size_expr

def generate_oob_snippet(index_var, allocated_size, element_size, instruction):
    """
    Generate a standard KLEE OOB write assertion plus the original instruction.
    """
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
        index_var, alloc_size, elem_size = parse_instruction(instruction)
    except ValueError as e:
        return str(e)

    snippet = generate_oob_snippet(index_var, alloc_size, elem_size, instruction)

    if not os.path.isfile(source_file):
        return f"[ERROR] Source file '{source_file}' does not exist."

    with open(source_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    insert_index = line_number - 1
    if insert_index < 0 or insert_index > len(lines):
        return f"[ERROR] line_number {line_number} is invalid for file with {len(lines)} lines."

    lines.insert(insert_index, snippet)

    source_dir = os.path.dirname(source_file)
    base_name = os.path.basename(source_file)
    name_part, ext_part = os.path.splitext(base_name)

    # Example: CharConverter_107_OOB_WRITE.c
    out_filename = f"{name_part}_{line_number}_{vuln_name}.c"
    out_path = os.path.join(source_dir, out_filename)


    with open(out_path, "w", encoding="utf-8") as out_f:
        out_f.writelines(lines)

    return f"[+] Inserted assertion at line {line_number} into '{out_path}'."

import argparse

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


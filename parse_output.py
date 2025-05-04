import json
import re
import os
import glob

def extract_data_from_content(content, input_file=""):
    # Extract assertion expression
    assertion_match = re.search(r"ASSERTION FAIL: (.+)", content)
    assertion_expr = assertion_match.group(1).strip() if assertion_match else ""

    # Extract full file path (do not shorten)
    file_match = re.search(r"File:\s+(.+\.c)", content)
    file_path = file_match.group(1).strip() if file_match else ""

    # Extract line number
    line_match = re.search(r"Line:\s+(\d+)", content)
    line = int(line_match.group(1)) if line_match else 0

    # Extract vulnerability type from driver file name
    vuln_type = ""
    base_name = os.path.basename(input_file)
    type_match = re.search(r'_([A-Z_]+)_\d+(?:_output)?\.txt$', base_name)
    vuln_type = type_match.group(1) if type_match else ""


    # Extract preconditions from "Preconditions:\n...Postconditions:"
    precondition = ""
    pre_match = re.search(r"Preconditions:\n(.*?)\n(?:Postconditions:|$)", content, re.DOTALL)
    if pre_match:
        precondition = pre_match.group(1).strip()

    # Collect symbolic variables
    variables_set = set()
    standard_var_pattern = r"(\w+) : \w+ = symbolic"
    variables_set.update(re.findall(standard_var_pattern, content))

    array_var_pattern = r"array ([\w\*]+(?:->\w+)?(?:\[\d+\])?) : \w+ -> \w+ = symbolic"
    variables_set.update(f"array {v}" for v in re.findall(array_var_pattern, content))

    return {
        "type": vuln_type,
        "file": file_path,
        "line": line,
        "variables": sorted(variables_set),
        "assertion": assertion_expr,
        "precondition": precondition
    }

def convert_file_to_json(input_path_or_dir, output_folder):
    if os.path.isfile(input_path_or_dir):
        input_files = [input_path_or_dir]
    else:
        input_files = glob.glob(os.path.join(input_path_or_dir, '*.txt'))

    os.makedirs(output_folder, exist_ok=True)

    for input_file in input_files:
        with open(input_file, 'r') as file:
            content = file.read()

        json_data = extract_data_from_content(content, input_file)
        output_file = os.path.join(output_folder, os.path.basename(input_file).replace('.txt', '.json'))

        with open(output_file, 'w') as file:
            file.write(json.dumps(json_data, indent=4))

        print(f'Formatted output saved to: {output_file}')

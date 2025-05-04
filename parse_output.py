import json
import re
import os
import glob

def extract_data_from_content(content, filename=""):
    # Extract assertion expression
    assertion_match = re.search(r"ASSERTION FAIL: (.+)", content)
    assertion_expr = assertion_match.group(1).strip() if assertion_match else ""

    # Extract file path and strip prefix
    file_match = re.search(r"File:\s+(.*\.c)", content)
    file_path = file_match.group(1).strip() if file_match else ""
    file_path = re.sub(r"^.*?/stase_generated/instrumented_source/", "", file_path)
    file_name = os.path.basename(file_path)

    # Extract line number
    line_match = re.search(r"Line:\s+(\d+)", content)
    line = int(line_match.group(1)) if line_match else 0

    # Infer type from filename (e.g., ..._OOB_WRITE_146.txt)
    vuln_type = ""
    if filename:
        m = re.search(r'_([A-Z_]+)_\d+\.txt$', filename)
        if m:
            vuln_type = m.group(1)

    # Extract precondition (entire SMT query block under "Preconditions:")
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
        "assertion": assertion_expr,
        "file": file_name,
        "line": line,
        "variables": sorted(variables_set),
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

        json_data = extract_data_from_content(content, filename=os.path.basename(input_file))

        output_file = os.path.join(output_folder, os.path.basename(input_file).replace('.txt', '.json'))

        with open(output_file, 'w') as file:
            file.write(json.dumps(json_data, indent=4))

        print(f'Formatted output saved to: {output_file}')

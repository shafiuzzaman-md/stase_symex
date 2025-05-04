import json
import re
import os
import glob

def extract_data_from_content(content):
    file_line_pattern = r"KLEE: ERROR: (.+?):(\d+): ASSERTION FAIL: (.+)"
    match = re.search(file_line_pattern, content)
    if match:
        path, line, assertion_fail = match.groups()
        file = os.path.basename(path)
    else:
        file, line, assertion_fail = '', '', ''

    if assertion_fail.startswith('!'):
        assertion_fail = assertion_fail[1:].strip()

    variables_set = set()
    standard_var_pattern = r"(\w+) : \w+ = symbolic"
    variables_set.update(re.findall(standard_var_pattern, content))

    array_var_pattern = r"array ([\w\*]+(?:->\w+)?(?:\[\d+\])?) : \w+ -> \w+ = symbolic"
    variables_set.update(f"array {v}" for v in re.findall(array_var_pattern, content))

    return {
        "type": assertion_fail.strip(),
        "file": file,
        "line": int(line) if line.isdigit() else 0,
        "variables": list(variables_set)
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

        json_data = extract_data_from_content(content)
        output_file = os.path.join(output_folder, os.path.basename(input_file).replace('.txt', '.json'))

        with open(output_file, 'w') as file:
            file.write(json.dumps(json_data, indent=4))

        print(f'Formatted output saved to: {output_file}')

import os
import re
import string

def simplify_smt_expressions(text):
    text = re.sub(r'array (\w+)\[\d+\] : w32 -> w8 = symbolic', r'\1 : int32 = symbolic', text)
    text = re.sub(r'\(ReadLSB w32 0 (\w+)\)', r'Read int32 \1', text)
    return text.replace('w64', 'int64').replace('false', 'FALSE')

def sanitize_for_filename(name):
    valid_chars = f"-_.() {string.ascii_letters}{string.digits}"
    return ''.join(c if c in valid_chars else '_' for c in name)[:100]

def extract_and_combine(source_filename, output_file_name):
    base_name = os.path.splitext(os.path.basename(source_filename))[0]

    # Go outside stase_symex/ to reach klee-last directory
    klee_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "stase_generated", "generated_klee_drivers", "klee-last"))

    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "stase_output"))
    os.makedirs(output_dir, exist_ok=True)

    combined_text = ""
    base_folder = None

    # Extract base folder (source file) from .assert.err
    for file in os.listdir(klee_dir):
        if file.endswith('.assert.err'):
            with open(os.path.join(klee_dir, file)) as f:
                for line in f:
                    if line.startswith("File:"):
                        m = re.search(r'File: .*\/(.*?)\.c', line)
                        if m:
                            base_folder = m.group(1)
                            break
            break

    if not base_folder:
        print(f"[!] Could not extract base folder name from .assert.err")
        return

    # Gather postconditions with assertion, file path, and line number
    postcondition_lines = []
    file_path = None
    assert_line = None

    for file in os.listdir(klee_dir):
        if file.endswith('.assert.err'):
            path = os.path.join(klee_dir, file)
            with open(path) as f:
                lines = f.readlines()
                for i, line in enumerate(lines):
                    if "ASSERTION FAIL:" in line:
                        postcondition_lines.append(line.strip())
                    elif line.startswith("File:"):
                        file_path = line.strip()
                    elif line.startswith("Line:"):
                        m = re.search(r'Line:\s*(\d+)', line)
                        if m:
                            assert_line = m.group(1)

    if not postcondition_lines:
        print("[!] No assertion failures found")
        return

    # Compose the postcondition text
    post_text = "Postconditions:\n"
    for line in postcondition_lines:
        post_text += f"{line}\n"
    if file_path:
        cleaned_path = re.sub(r'\.\./inputs/\.\./stase_generated/instrumented_source/', '', file_path)
        post_text += f"{cleaned_path}\n"

    if assert_line:
        post_text += f"Line: {assert_line}\n"

    # Simplify it
    post_text = simplify_smt_expressions(post_text)


    # Gather preconditions from a matching .kquery
    for file in os.listdir(klee_dir):
        if file.endswith('.kquery'):
            with open(os.path.join(klee_dir, file)) as kf:
                kquery = kf.read()
                pre_text = "Preconditions:\n" + simplify_smt_expressions(kquery)
                combined_text = pre_text + "\n" + post_text
                break

    output_path = os.path.join(output_dir, output_file_name)
    with open(output_path, 'w') as out:
        out.write(combined_text)
    print(f"[✓] Extracted: {output_path}")

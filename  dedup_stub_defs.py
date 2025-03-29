def dedup_stub_defs(file_path):
    seen = set()
    deduped_lines = []

    with open(file_path, 'r') as f:
        for line in f:
            stripped = line.strip()

            # Only dedup non-empty and non-comment lines
            if stripped and not stripped.startswith('//'):
                # Normalize line for deduplication
                if stripped.endswith('= {0};') or stripped.endswith('= 0;'):
                    key = stripped.rsplit('=', 1)[0].strip() + ';'
                else:
                    key = stripped
                if key not in seen:
                    seen.add(key)
                    deduped_lines.append(line)
            else:
                deduped_lines.append(line)

    with open(file_path, 'w') as f:
        f.writelines(deduped_lines)


if __name__ == '__main__':
    dedup_stub_defs('global_stub_defs.c')

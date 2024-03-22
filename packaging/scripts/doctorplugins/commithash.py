def post_run(doctorfn):
    print("Doctoring commit hash ...")
    target_hash = get_target_commit_hash()
    with doctorfn('product.json') as data:
        if 'commit' not in data[0]:
            print("'commit' key is not in product.json. Skipping.")
            return
        if data[0]['commit'] == target_hash:
            print("Commit hash already the same. Skipping.")
            return
        data[0]['commit'] = target_hash
        data[1] = True

def get_target_commit_hash():
    # get target commit hash
    chline = None
    src_str = 'final-commit:'
    with open('patches/patches.list', 'r') as f:
        for l in f:
            l = l.strip()
            if l.startswith(src_str):
                chline = l
                break

    if chline is None:
        raise ValueError("'final-commit' line not found.")

    target_hash = chline[len(src_str) + 1:].strip()
    return target_hash

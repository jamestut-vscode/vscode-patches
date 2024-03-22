def pre_run(doctorfn):
    print("Updating version string ...")
    target_version = get_target_version()
    with doctorfn('package.json') as data:
        if data[0]['version'] == target_version:
            print("Version string already set. Skipping.")
            return
        data[0]['version'] = target_version
        data[1] = True

def get_target_version():
    with open('version.txt', 'r') as f:
        return f.read().strip()

import json

def pre_run(doctorfn):
    with open('version.json', 'r') as f:
        d = json.load(f)
    electron_version = d.get('electronVersion')
    if electron_version is None:
        return
    with doctorfn('package.json') as context:
        if context.data['devDependencies']['electron'] != electron_version:
            print("Updating Electron dev dependency ...")
            context.data['devDependencies']['electron'] = electron_version
            context.modified = True

def get_target_versions():
    with open('version.json', 'r') as f:
        d = json.load(f)
    return d['productVersion'], d['ipcVersion']

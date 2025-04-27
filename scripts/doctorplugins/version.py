import json

def pre_run(doctorfn):
    print("Updating version string ...")
    product_version, ipc_version = get_target_versions()
    with doctorfn('package.json') as context:
        if context.data['version'] != product_version:
            print("Updating package version string ...")
            context.data['version'] = product_version
            context.modified = True
    with doctorfn('product.json') as context:
        if context.data.get('ipcVersion') != ipc_version:
            print("Updating IPC version string ...")
            context.data['ipcVersion'] = ipc_version
            context.modified = True

def get_target_versions():
    with open('version.json', 'r') as f:
        d = json.load(f)
    return d['productVersion'], d['ipcVersion']

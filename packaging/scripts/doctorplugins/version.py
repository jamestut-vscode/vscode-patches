import json

def pre_run(doctorfn):
    print("Updating version string ...")
    product_version, ipc_version = get_target_versions()
    with doctorfn('package.json') as data:
        if data[0]['version'] != product_version:
            print("Updating package version string ...")
            data[0]['version'] = product_version
            data[1] = True
    with doctorfn('product.json') as data:
        if data[0].get('ipcVersion') != ipc_version:
            print("Updating IPC version string ...")
            data[0]['ipcVersion'] = ipc_version
            data[1] = True

def get_target_versions():
    with open('version.json', 'r') as f:
        d = json.load(f)
    return d['productVersion'], d['ipcVersion']

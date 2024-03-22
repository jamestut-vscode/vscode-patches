def pre_run(doctorfn):
    print("Updating darwin bundle ID ...")
    target_key = 'darwinBundleIdentifier'
    target_bundle_id = 'com.saylor.vscode.oss'
    with doctorfn('product.json') as data:
        # deliberate as we expect this plugin to be run on '--pre'
        if data[0][target_key] == target_bundle_id:
            print("macOS bundle identifier already set. Skipping.")
        data[0][target_key] = target_bundle_id
        data[1] = True

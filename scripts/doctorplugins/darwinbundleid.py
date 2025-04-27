def pre_run(doctorfn):
    print("Updating darwin bundle ID ...")
    target_key = 'darwinBundleIdentifier'
    target_bundle_id = 'com.saylor.vscode.oss'
    with doctorfn('product.json') as context:
        # deliberate as we expect this plugin to be run on '--pre'
        if context.data[target_key] == target_bundle_id:
            print("macOS bundle identifier already set. Skipping.")
        context.data[target_key] = target_bundle_id
        context.modified = True

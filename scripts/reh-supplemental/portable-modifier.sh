TARGET_SYSROOT="$ROOT"/sysroot
if [[ "$("$ROOT/patchelf" --print-rpath "$ROOT/node")" != "$TARGET_SYSROOT" ]]
then
    "$ROOT/patchelf" --set-rpath "$TARGET_SYSROOT" "$ROOT/node"
    "$ROOT/patchelf" --set-interpreter "$TARGET_SYSROOT/$$LD_NAME$$" "$ROOT/node"
fi

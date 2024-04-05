#!/usr/bin/env zsh

# Create packaged Linux REH from the given macOS REH

set -e

if [[ $# -ne 3 ]]
then
    echo "Usage: ${0:t} (Linux REH folder) (official Linux REH archive) (output)"
    exit 1
fi

SCRIPTPATH="${0:a:h}"
OUTFILE="${3:a}"

# output must be .zip
if [[ ${3:e:t} != 'zip' ]]
then
    echo "Output file must be a .zip file"
    exit 1
fi

OUTNAME="${3:r:t}"

OUTDIR="work/$OUTNAME"
cp -r "$1" "$OUTDIR"
# working directory to extract official Linux files
LINUX_WORKDIR_BASE="$OUTDIR/linux-work"
mkdir "$LINUX_WORKDIR_BASE"

# extract Linux files
echo "Extracting official Linux REH files ..."
tar -C "$LINUX_WORKDIR_BASE" -xf "$2"
# determine extracted REH location
LINUX_WORKDIR="$LINUX_WORKDIR_BASE/$(ls "$LINUX_WORKDIR_BASE")"

# replace node files on target
echo "Replacing files ..."
for TGT in node node_modules
do
    rm -rf "$OUTDIR/$TGT"
    mv "$LINUX_WORKDIR/$TGT" "$OUTDIR/$TGT"
done

echo "Removing official Linux REH files ..."
rm -rf "$LINUX_WORKDIR_BASE"

echo "Creating archive ..."
cd work
"$SCRIPTPATH/create-archive.sh" "$OUTNAME" "$OUTFILE"

echo "Cleaning up files ..."
rm -rf "$OUTNAME"

echo "Done!"

#!/bin/sh
# Copy what the host's cron runs out of this image (jikhanjung P11). The entrypoint calls it
# at every container start, so a release also updates the daily refresh it drives.
#
#   install.sh [destination]     default $PRESENT_SCRIPTS_DIR, else nothing to do
#
# Copied: deploy/cron/present.sh, scripts/fetch_present_weather.py, scripts/present_catalogue.py
# and requirements-present.txt, plus INSTALLED (version and time). Not copied: the venv, which
# the host builds itself (present.sh). Without a writable destination it does nothing and
# says so: the site serves either way.
set -eu
dest="${1:-${PRESENT_SCRIPTS_DIR:-}}"
if [ -z "$dest" ] || [ ! -d "$dest" ] || [ ! -w "$dest" ]; then
    echo "cron scripts: no writable ${dest:-destination}; not installed"
    exit 0
fi
stage="$dest/.new"
rm -rf "$stage"
mkdir -p "$stage"
cp /app/deploy/cron/present.sh /app/scripts/fetch_present_weather.py /app/scripts/present_catalogue.py \
   /app/requirements-present.txt "$stage/"
chmod 755 "$stage/present.sh"
chmod 644 "$stage/fetch_present_weather.py" "$stage/present_catalogue.py" "$stage/requirements-present.txt"
echo "${EARTHTHRUTIME_VERSION:-?} $(date -u +%Y-%m-%dT%H:%MZ)" > "$stage/INSTALLED"
# Each file replaced whole, so a cron run that starts mid-copy reads old or new, never half.
for file in "$stage"/*; do
    mv -f "$file" "$dest/$(basename "$file")"
done
rmdir "$stage"
echo "cron scripts: installed into $dest ($(cat "$dest/INSTALLED"))"

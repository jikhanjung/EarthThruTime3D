#!/usr/bin/env bash
# Remove old releases, keeping the running one and enough history to roll back.
#
# Only this service's own artefacts are touched: images under its repository name, its
# data directories, and its release tarballs. Nothing global is pruned, because this
# host runs other services whose caches and images are not ours to reclaim.
set -euo pipefail
cd "$(dirname "$0")"
keep=${KEEP:-2}                 # how many versions survive, the running one included
release_dir=${RELEASE_DIR:-$HOME/earththrutime3d-release}
repository=honestjung/earththrutime3d
dry_run=${DRY_RUN:-0}

[[ -f .env ]] || { echo 'No .env; nothing has been deployed here.' >&2; exit 1; }
current=$(grep -oP '(?<=^IMAGE_TAG=).*' .env)
[[ -n "$current" ]] || { echo 'No IMAGE_TAG in .env.' >&2; exit 1; }

# Every version this host knows about, from either source, newest first.
mapfile -t versions < <(
    { ls -1 data 2>/dev/null | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' || true
      docker images "$repository" --format '{{.Tag}}' | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' || true
    } | sort -Vru)

# The running version is kept whatever its age, then the newest others fill the quota.
survivors=("$current")
for version in "${versions[@]}"; do
    [[ "$version" == "$current" ]] && continue
    (( ${#survivors[@]} >= keep )) && break
    survivors+=("$version")
done
keeping=" ${survivors[*]} "
echo "Running $current; keeping${keeping% }."

before=$(df --output=avail -k / | tail -1)
removed=0
for version in "${versions[@]}"; do
    [[ "$keeping" == *" $version "* ]] && continue
    echo "removing $version"
    removed=$((removed + 1))
    if (( dry_run )); then continue; fi
    # An image still in use refuses to go, which is the safety net rather than a problem.
    docker image rm "$repository:$version" >/dev/null 2>&1 || echo "  image in use or absent"
    rm -rf -- "data/$version"
    rm -f -- "$release_dir"/*-"$version".tar.gz "$release_dir/SHA256SUMS-$version"
done

if (( dry_run )); then
    echo "Dry run: $removed versions would be removed."
    exit 0
fi
after=$(df --output=avail -k / | tail -1)
# awk rather than bc: bc is not installed on this host and is not worth adding for one sum.
awk -v removed="$removed" -v before="$before" -v after="$after" \
    'BEGIN { printf "Removed %d versions; %.1f GiB free, %+.0f MiB reclaimed.\n",
             removed, after / 1048576, (after - before) / 1024 }' 

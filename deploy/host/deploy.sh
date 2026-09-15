#!/usr/bin/env bash
# The image and its matching data directory must already be on the host.
# Order: verify the pair, back up the database, swap, smoke. Any failure rolls back to
# the previous service configuration. Code rollback and data restore stay separate:
# this script never touches db/ except to snapshot it.
set -euo pipefail
cd "$(dirname "$0")"
version=${1:-}
[[ "$version" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo 'Usage: bash deploy.sh vX.Y.Z'; exit 1; }
[[ -f .env.django ]] || { echo 'Prepare .env.django first.'; exit 1; }
[[ -f "data/$version/manifest.json" ]] || { echo "Prepare data/$version first."; exit 1; }
mkdir -p db backups
docker image inspect "honestjung/earththrutime3d:$version" >/dev/null

# Validate the exact immutable image and data pair before touching the running service.
docker run --rm --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m \
    --mount "type=bind,src=$PWD/data/$version,dst=/runtime,readonly" \
    --entrypoint python "honestjung/earththrutime3d:$version" /app/deploy/verify_bundle.py

# Snapshot before the swap, using the image already on the host. Code rollback and
# data restore stay separate: nothing below writes to db/.
bash backup.sh "$version"

next_env=$(mktemp .env.next.XXXXXX)
trap 'rm -f "$next_env"' EXIT
python3 update_compose_env.py "$version" "$next_env"
docker compose --env-file "$next_env" config --quiet
if [[ -f .env ]]; then cp .env .env.previous; fi
mv "$next_env" .env
if ! docker compose up -d --wait --wait-timeout 90 \
    || ! docker compose exec -T earththrutime3d python /app/deploy/healthcheck.py </dev/null \
    || ! bash smoke.sh "${version#v}"; then
    docker compose logs --tail 50
    if [[ -f .env.previous ]]; then
        cp .env.previous .env
        docker compose up -d --wait --wait-timeout 90
    fi
    echo 'Deployment failed; inspect logs.' >&2
    exit 1
fi
docker compose ps
echo "Deployed $version. Rollback uses the same command with the previous version."

#!/usr/bin/env bash
# Build on the development host. The server only pulls or loads the result.
set -euo pipefail
cd "$(dirname "$0")/.."
version=${1:-$(cat deploy/DOCKER_VERSION)}
[[ "$version" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo 'Usage: bash deploy/build.sh vX.Y.Z' >&2; exit 1; }
[[ "$version" == "$(cat deploy/DOCKER_VERSION)" ]] || { echo 'Update deploy/DOCKER_VERSION first.' >&2; exit 1; }
python_bin=${PYTHON:-.venv/bin/python}
[[ -x "$python_bin" ]] || python_bin=python3
app_version=$("$python_bin" -c 'from config.version import VERSION; print(VERSION)')
[[ "$version" == "v$app_version" ]] || { echo "deploy/DOCKER_VERSION and config/version.py disagree: $version vs v$app_version" >&2; exit 1; }
image="honestjung/earththrutime3d:$version"

# Preflight: the suites that gate a release, then the runtime bundle.
"$python_bin" manage.py check
"$python_bin" manage.py makemigrations --check --dry-run
"$python_bin" manage.py test
"$python_bin" deploy/pack_data.py "$version"

revision=$(git rev-parse --short HEAD)
if [[ -n "$(git status --porcelain)" ]]; then revision="$revision-dirty"; fi
docker build --platform linux/amd64 -f deploy/Dockerfile \
    --build-arg "APP_VERSION=$version" --build-arg "VCS_REF=$revision" -t "$image" .
"$python_bin" deploy/smoke_image.py "$image" ".build/runtime-$version"

mkdir -p dist
docker save "$image" | gzip > "dist/earththrutime3d-image-$version.tar.gz"
tar -czf "dist/earththrutime3d-host-$version.tar.gz" -C deploy/host .
(
    cd dist
    sha256sum "earththrutime3d-image-$version.tar.gz" "earththrutime3d-data-$version.tar.gz" \
        "earththrutime3d-host-$version.tar.gz" > "SHA256SUMS-$version"
)
docker image inspect "$image" --format 'Built {{.RepoTags}} {{.Id}} ({{.Size}} bytes)'
echo "Release files are in dist/. See deploy/README.md for the dolfinid procedure."

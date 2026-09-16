"""Run the built image the way the server will, then check what it actually serves.

Covers the three things a build can get wrong without failing: the image quietly
carrying the published maps, the viewer coming up without its fields, and the licence
decision not being honoured by the running code.
"""
import json
import gzip
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]


def free_port():
    """Ask the kernel for an unused port rather than assuming one.

    A fixed port collides with whatever else the build host happens to be running, and
    the failure surfaces as an unexplained container exit.
    """
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


PORT = free_port()


def run(*command, **kwargs):
    return subprocess.run(command, check=True, text=True, capture_output=True, **kwargs).stdout


def fetch(path, expect=200):
    url = f"http://127.0.0.1:{PORT}{path}"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            body = response.read()
            status = response.status
    except urllib.error.HTTPError as error:
        body, status = error.read(), error.code
    if status != expect:
        raise SystemExit(f"{path}: expected {expect}, got {status}")
    return body


def main():
    image, runtime = sys.argv[1], Path(sys.argv[2]).resolve()
    version = image.rsplit(":", 1)[1].lstrip("v")

    listing = run("docker", "run", "--rm", "--entrypoint", "sh", image, "-c",
                  "find / -xdev -name '*.jpg' -o -xdev -name '*.jpeg' | head -20")
    if listing.strip():
        raise SystemExit("Image contains JPEG files; the published maps must stay out:\n" + listing)

    with tempfile.TemporaryDirectory() as database:
        Path(database).chmod(0o777)
        container = run(
            "docker", "run", "-d", "--rm", "--read-only",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
            "--mount", f"type=bind,src={runtime},dst=/runtime,readonly",
            "--mount", f"type=bind,src={database},dst=/var/lib/earththrutime3d",
            "-p", f"127.0.0.1:{PORT}:8000",
            "-e", "SECRET_KEY=smoke-test-only-secret-0000000000000000000000000000000000",
            "-e", "ALLOWED_HOSTS=127.0.0.1,localhost",
            "-e", "SECURE_SSL_REDIRECT=false",
            "-e", "SCOTESE_VIEWER_ENABLED=true",
            "-e", "SCOTESE_SOURCE_MAPS_PUBLIC=false",
            image).strip()
        try:
            report = None
            for _ in range(60):
                try:
                    report = json.loads(fetch("/healthz"))
                    break
                except (SystemExit, urllib.error.URLError, ConnectionError):
                    time.sleep(1)
            if report is None:
                raise SystemExit("Container never became healthy:\n"
                                 + run("docker", "logs", container))
            if report["status"] != "ok" or report["version"] != version:
                raise SystemExit(f"Unexpected health report: {report}")
            if (report["fields"]["missing"] or report["fields"]["expected"] != 90
                    or report["fields"].get("source") != "paleoatlas2016"):
                raise SystemExit(f"Land fields not served: {report['fields']}")

            home = fetch("/").decode()
            for needle in ("globe-frames", "globe-stops", "globe-motions", "scotese.com"):
                if needle not in home:
                    raise SystemExit(f"Home page is missing {needle}.")
            if "/globe/maps/" in home:
                raise SystemExit("Home page offers the published maps.")
            if 'id="surface"' in home:
                raise SystemExit("Surface toggle is offered without the published maps.")
            fetch("/globe/maps/scotese-000.jpg", expect=404)
            fetch("/globe/fields/scotese-000.png")
            fetch("/globe/fields/paleoatlas-000.png")
            fetch("/globe/maps/paleoatlas-000.jpg", expect=404)
            if "globe-coastlines" not in home:
                raise SystemExit("The fossil coastline layer is not offered over the atlas.")
            if not json.loads(fetch("/globe/coastlines/255.json")).get("rings"):
                raise SystemExit("PaleoCoastlines at 255 Ma are empty.")
            fetch("/globe/coastlines/3.json", expect=404)
            if "globe-frames" not in fetch("/?masks=scotese2002").decode():
                raise SystemExit("The 2002 comparison masks are not reachable.")
            # The plate model is a second dataset with its own licence; it must be both
            # served and credited, and nothing outside its three files reachable.
            about = fetch("/about/").decode()
            shapes = 0
            for model in ("merdith2021", "muller2022", "cao2024", "matthews2016",
                          "paleomap2016"):
                rotations = json.loads(fetch(f"/plates/{model}/rotations.json"))
                if not rotations.get("sequences"):
                    raise SystemExit(f"{model}: rotations are empty.")
                continents = json.loads(fetch(f"/plates/{model}/continents.json"))
                # Models draw their continents at different granularities, so the floor
                # only has to catch a bundle that arrived empty or half-written.
                if len(continents.get("features", [])) < 250:
                    raise SystemExit(f"{model}: continents look truncated "
                                     f"({len(continents.get('features', []))} features).")
                shapes = len(continents["features"])
                citation = continents["attribution"]["citation"].split(",")[0]
                if citation not in about:
                    raise SystemExit(f"{model} is served without its citation on /about/.")
            fetch("/plates/merdith2021/secret.json", expect=404)
            fetch("/plates/nope/rotations.json", expect=404)
            if "Creative Commons" not in about:
                raise SystemExit("The plate models are served without their licence.")
            fetch("/static/core/globe.js")
            collision = fetch('/collision/').decode()
            region_manifest = json.loads((runtime/'india-asia/catalogue.json').read_text())
            region_url = '/collision/data/' + region_manifest['sha256'][:16] + '.json'
            if region_url not in collision or 'collision-surface' not in collision:
                raise SystemExit('Collision popup has no data/terrain')
            region = json.loads(fetch(region_url))
            if [f['age_ma'] for f in region['frames']] != [80, 60, 40, 20, 0]:
                raise SystemExit('Collision ages are missing')
            request = urllib.request.Request(f'http://127.0.0.1:{PORT}'+region_url,
                                             headers={'Accept-Encoding': 'gzip'})
            with urllib.request.urlopen(request) as response:
                if response.headers.get('Content-Encoding') != 'gzip':
                    raise SystemExit('Collision gzip response missing')
                if json.loads(gzip.decompress(response.read())) != region:
                    raise SystemExit('Collision compressed data differs')
            if 'mantle-frames' not in fetch('/mantle/').decode():
                raise SystemExit('Mantle data missing')
            mantle = json.loads((runtime/'mantle/muller2022-opt1/catalogue.json').read_text())
            for layer in mantle['frames'][-1]['layers'].values():
                fetch('/mantle/assets/'+layer['file'])
            fetch('/static/core/collision-surface.js')
            crust = json.loads((runtime/'crust/catalogue.json').read_text())
            fetch('/crust/assets/' + crust['asset']['file'])
            fetch('/static/core/crust.js')
            fetch("/about/")
            print(f"Smoke passed: {version}, {report['fields']['expected']} land fields, "
                  f"five plate models, {shapes} shapes in the last, "
                  "no published maps served.")
        finally:
            subprocess.run(["docker", "stop", container], check=False, capture_output=True)


if __name__ == "__main__":
    main()

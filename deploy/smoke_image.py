"""Run the built image the way the server will, then check what it actually serves.

Covers the three things a build can get wrong without failing: the image quietly
carrying the published maps, the viewer coming up without its fields, and the licence
decision not being honoured by the running code.
"""
import json
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
PORT = 18014


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
            fields = report["fields"]
            if fields.get("series") != "paleodem" or fields["missing"] or fields["expected"] != 110:
                raise SystemExit(f"Elevation series not served: {fields}")

            home = fetch("/").decode()
            for needle in ("globe-frames", "globe-stops", "globe-motions", "scotese.com",
                           "zenodo.org/records/5460860"):
                if needle not in home:
                    raise SystemExit(f"Home page is missing {needle}.")
            if "/globe/maps/" in home:
                raise SystemExit("Home page offers the published maps.")
            fetch("/globe/maps/scotese-000.jpg", expect=404)
            fetch("/globe/fields/scotese-000.png")
            fetch("/globe/fields/scotese-650.png")
            fetch("/globe/fields/paleodem-0000.png")
            fetch("/static/core/globe.js")
            fetch("/about/")
            print(f"Smoke passed: {version}, {fields['series']} series, {fields['expected']} "
                  "fields, no published maps served.")
        finally:
            subprocess.run(["docker", "stop", container], check=False, capture_output=True)


if __name__ == "__main__":
    main()

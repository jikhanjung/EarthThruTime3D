#!/usr/bin/env python3
"""Check this project's rotation composition against the GPlates Web Service.

The rotation file is the model; composing it correctly is our responsibility. The
service runs the reference implementation, so disagreeing with it means we are wrong.
Needs network access, so it is a script rather than part of the offline suites.
"""
import argparse
import json
import math
import random
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rotation_model import RotationModel  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ROTATION = ROOT / "data/sources/plates/merdith2021/1000_0_rotfile_Merdith_et_al.rot"
SERVICE = "https://gws.gplates.org/reconstruct/reconstruct_points/"


def separation(first, second):
    """Angle between two lon/lat points, in degrees."""
    lat1, lon1, lat2, lon2 = (math.radians(value) for value in
                              (first[1], first[0], second[1], second[0]))
    cosine = (math.sin(lat1) * math.sin(lat2)
              + math.cos(lat1) * math.cos(lat2) * math.cos(lon2 - lon1))
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def ask(plate, at, longitude, latitude, model):
    url = (f"{SERVICE}?points={longitude},{latitude}&time={at}"
           f"&model={model}&pid={plate}")
    result = subprocess.run(["curl", "-s", "--max-time", "30", url],
                            capture_output=True, text=True)
    payload = json.loads(result.stdout)
    return payload["coordinates"][0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=40)
    parser.add_argument("--tolerance", type=float, default=0.001,
                        help="degrees of arc; the service reports four decimals")
    parser.add_argument("--model", default="MERDITH2021")
    parser.add_argument("--seed", type=int, default=20260913)
    args = parser.parse_args()

    model = RotationModel(ROTATION)
    plates = model.plates()
    random.seed(args.seed)
    checked = worst = 0
    failures = []
    while checked < args.samples:
        plate = random.choice(plates)
        at = round(random.uniform(1.0, 900.0), 1)
        try:
            ours = model.reconstruct(plate, at, random.uniform(-180, 180),
                                     random.uniform(-80, 80))
        except ValueError:
            continue  # The plate does not exist at that time; nothing to compare.
        longitude, latitude = random.uniform(-180, 180), random.uniform(-80, 80)
        ours = model.reconstruct(plate, at, longitude, latitude)
        theirs = ask(plate, at, longitude, latitude, args.model)
        apart = separation(ours, theirs)
        worst = max(worst, apart)
        if apart > args.tolerance:
            failures.append((plate, at, ours, theirs, apart))
        checked += 1
        time.sleep(0.15)

    print(f"Checked {checked} reconstructions against {args.model}.")
    print(f"Worst separation: {worst:.6f} degrees (tolerance {args.tolerance}).")
    for plate, at, ours, theirs, apart in failures:
        print(f"  plate {plate} at {at} Ma: ours {ours}, service {theirs}, {apart:.4f} deg")
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()

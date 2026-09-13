"""Read a GPlates rotation file and compose plate rotations at any time.

A rotation file is a list of total reconstruction poles: for a moving plate, a time, a
pole and an angle, all relative to a fixed plate. Reconstructing a plate to a time means
walking the chain of fixed plates up to the anchor and composing what is found, and
interpolating inside a sequence when the asked-for time falls between two samples.

This is the piece that makes a time continuous rather than a slot in a list of pictures.
"""
import math
from collections import defaultdict
from pathlib import Path

ANCHOR = 0


def _quaternion(pole_lat, pole_lon, angle_degrees):
    """Axis and angle to a unit quaternion, the form that composes and interpolates."""
    latitude = math.radians(pole_lat)
    longitude = math.radians(pole_lon)
    axis = (math.cos(latitude) * math.cos(longitude),
            math.cos(latitude) * math.sin(longitude),
            math.sin(latitude))
    half = math.radians(angle_degrees) / 2.0
    scale = math.sin(half)
    return (math.cos(half), axis[0] * scale, axis[1] * scale, axis[2] * scale)


IDENTITY = (1.0, 0.0, 0.0, 0.0)


def multiply(first, second):
    a, b, c, d = first
    e, f, g, h = second
    return (a * e - b * f - c * g - d * h,
            a * f + b * e + c * h - d * g,
            a * g - b * h + c * e + d * f,
            a * h + b * g - c * f + d * e)


def conjugate(quaternion):
    w, x, y, z = quaternion
    return (w, -x, -y, -z)


def slerp(start, end, fraction):
    """Shortest-arc interpolation between two rotations."""
    dot = sum(a * b for a, b in zip(start, end))
    if dot < 0.0:
        end = tuple(-value for value in end)
        dot = -dot
    if dot > 0.9999995:
        blended = tuple(a + (b - a) * fraction for a, b in zip(start, end))
    else:
        theta = math.acos(max(-1.0, min(1.0, dot)))
        sine = math.sin(theta)
        first = math.sin((1.0 - fraction) * theta) / sine
        second = math.sin(fraction * theta) / sine
        blended = tuple(a * first + b * second for a, b in zip(start, end))
    norm = math.sqrt(sum(value * value for value in blended)) or 1.0
    return tuple(value / norm for value in blended)


def rotate(quaternion, longitude, latitude):
    """Apply a rotation to a point given in degrees, returning degrees."""
    lon = math.radians(longitude)
    lat = math.radians(latitude)
    point = (0.0, math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat))
    w, x, y, z = multiply(multiply(quaternion, point), conjugate(quaternion))
    return (math.degrees(math.atan2(y, x)),
            math.degrees(math.asin(max(-1.0, min(1.0, z)))))


class RotationModel:
    def __init__(self, path):
        # Samples per (moving plate, fixed plate), in time order. A plate can change
        # which plate it is measured against part way through its history, so the fixed
        # plate is part of the key rather than a property of the moving plate.
        self.sequences = defaultdict(list)
        for line in Path(path).read_text(errors="replace").splitlines():
            body = line.split("!", 1)[0].split()
            if len(body) < 6:
                continue
            try:
                moving = int(body[0])
                time = float(body[1])
                pole_lat, pole_lon, angle = (float(value) for value in body[2:5])
                fixed = int(body[5])
            except ValueError:
                continue
            if any(math.isnan(value) for value in (time, pole_lat, pole_lon, angle)):
                continue
            self.sequences[(moving, fixed)].append((time, pole_lat, pole_lon, angle))
        for samples in self.sequences.values():
            samples.sort(key=lambda sample: sample[0])
        self.by_moving = defaultdict(list)
        for (moving, fixed), samples in self.sequences.items():
            self.by_moving[moving].append((fixed, samples[0][0], samples[-1][0]))

    def plates(self):
        return sorted(self.by_moving)

    def _relative(self, samples, time):
        """The pole for one moving/fixed pair at `time`, or None outside its span."""
        if not samples or time < samples[0][0] - 1e-9 or time > samples[-1][0] + 1e-9:
            return None
        previous = samples[0]
        for sample in samples:
            if sample[0] >= time - 1e-9:
                if abs(sample[0] - previous[0]) < 1e-9 or abs(sample[0] - time) < 1e-9:
                    return _quaternion(sample[1], sample[2], sample[3])
                fraction = (time - previous[0]) / (sample[0] - previous[0])
                # Interpolate the rotation from the earlier sample to the later one,
                # which is how a stage rotation is split, rather than the poles.
                start = _quaternion(previous[1], previous[2], previous[3])
                end = _quaternion(sample[1], sample[2], sample[3])
                stage = multiply(conjugate(start), end)
                return multiply(start, slerp(IDENTITY, stage, fraction))
            previous = sample
        return _quaternion(samples[-1][1], samples[-1][2], samples[-1][3])

    def rotation(self, plate, time, anchor=ANCHOR, _seen=None):
        """Total rotation of `plate` relative to `anchor` at `time`."""
        if plate == anchor:
            return IDENTITY
        seen = set() if _seen is None else _seen
        if plate in seen:
            raise ValueError(f"Rotation chain loops at plate {plate}")
        seen = seen | {plate}
        # 32 of this model's plates carry overlapping sequences: a narrow window
        # inserted over a broad one to say that for those years the plate is measured
        # against a different neighbour. The narrower, later-starting sequence is the
        # statement being made, so it wins where they overlap.
        for fixed, start, end in sorted(self.by_moving.get(plate, []),
                                        key=lambda entry: entry[1], reverse=True):
            if not start - 1e-9 <= time <= end + 1e-9:
                continue
            relative = self._relative(self.sequences[(plate, fixed)], time)
            if relative is None:
                continue
            upstream = self.rotation(fixed, time, anchor, seen)
            return multiply(upstream, relative)
        raise ValueError(f"No rotation for plate {plate} at {time} Ma")

    def reconstruct(self, plate, time, longitude, latitude, anchor=ANCHOR):
        return rotate(self.rotation(plate, time, anchor), longitude, latitude)

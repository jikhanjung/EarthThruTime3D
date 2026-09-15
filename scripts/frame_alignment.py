"""Coordinate primitives for audits; column vectors, right-handed geographic xyz.

These transformations change coordinates, not the physical reference frame by fiat.
"""
import numpy as np

EARTH_RADIUS_KM = 6371.0
# Same local axes as globe.js onSphere; the earth group's camera rotation is separate.
GEOGRAPHIC_TO_GLOBE = np.array([[1., 0., 0.], [0., 0., 1.], [0., -1., 0.]])


def unit(points):
    points = np.asarray(points, dtype=float)
    lengths = np.linalg.norm(points, axis=-1, keepdims=True)
    if not np.all(np.isfinite(points)) or np.any(lengths < 1e-12):
        raise ValueError('Expected finite nonzero vectors')
    return points / lengths


def lonlat_xyz(longitude, latitude, depth_km=0):
    longitude, latitude, depth = np.broadcast_arrays(longitude, latitude, depth_km)
    if not all(np.all(np.isfinite(a)) for a in (longitude, latitude, depth)) or np.any(np.abs(latitude) > 90):
        raise ValueError('Finite coordinates and latitude in [-90, 90] required')
    lon, lat = np.deg2rad(longitude), np.deg2rad(latitude)
    radius = 1 - depth / EARTH_RADIUS_KM
    if np.any(radius <= 0) or np.any(radius > 1):
        raise ValueError('Depth must lie between surface and centre (exclusive)')
    return np.stack([np.cos(lat)*np.cos(lon), np.cos(lat)*np.sin(lon), np.sin(lat)], axis=-1)*np.expand_dims(radius, -1)


def apply(matrix, points):
    return np.asarray(points) @ np.asarray(matrix).T


def quaternion_matrix(quaternion):
    q = unit(quaternion)
    w, x, y, z = q
    return np.array([[1-2*(y*y+z*z), 2*(x*y-w*z), 2*(x*z+w*y)],
                     [2*(x*y+w*z), 1-2*(x*x+z*z), 2*(y*z-w*x)],
                     [2*(x*z-w*y), 2*(y*z+w*x), 1-2*(x*x+y*y)]])


def fit_rotation(source, target):
    """Origin-constrained proper rotation (no translation, scaling or reflection)."""
    a, b = unit(source), unit(target)
    if a.shape != b.shape or a.ndim != 2 or a.shape[1] != 3 or len(a) < 3:
        raise ValueError('At least three paired xyz vectors required')
    if np.linalg.matrix_rank(a, tol=1e-8) < 2:
        raise ValueError('Collinear points do not constrain rotation')
    u, _, vt = np.linalg.svd(a.T @ b)
    return vt.T @ np.diag([1, 1, np.linalg.det(vt.T @ u.T)]) @ u.T


def separation_degrees(a, b):
    a, b = unit(a), unit(b)
    return np.rad2deg(np.arctan2(np.linalg.norm(np.cross(a, b), axis=-1), np.sum(a*b, axis=-1)))


def rotation_degrees(matrix):
    return float(np.rad2deg(np.arccos(np.clip((np.trace(matrix)-1)/2, -1, 1))))


def transform_section(matrix, longitude=85):
    """Rotate the meridian's normal AND selected half-plane with its points."""
    a = np.deg2rad(longitude)
    return apply(matrix, [-np.sin(a), np.cos(a), 0]), apply(matrix, [np.cos(a), np.sin(a), 0])

import * as THREE from 'three';

// Rendering samples only: keep the source endpoints and their great-circle path.
// At 0.1 degrees a chord sags < 4e-7 Earth radii, below the existing line clearance.
export function densifySegments(points, maxAngle = Math.PI / 1800) {
  const result = [];
  for (let i = 0; i < points.length; i += 2) {
    const a = points[i], b = points[i + 1];
    const start = a.clone().normalize(), end = b.clone().normalize();
    const angle = start.angleTo(end);
    const steps = Math.max(1, Math.ceil(angle / maxAngle));
    const rotation = new THREE.Quaternion().setFromUnitVectors(start, end);
    let previous = a;
    for (let j = 1; j <= steps; j++) {
      const fraction = j / steps;
      const here = j === steps ? b : start.clone()
        .applyQuaternion(new THREE.Quaternion().slerp(rotation, fraction))
        .multiplyScalar(THREE.MathUtils.lerp(a.length(), b.length(), fraction));
      result.push(previous, here);
      previous = here;
    }
  }
  return result;
}

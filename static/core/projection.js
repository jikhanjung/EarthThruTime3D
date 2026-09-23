// Mollweide forward projection, normalized to an ellipse of radius 1.
// Image -> sphere uses inverse sampling: each output lon/lat samples this ellipse.
export function mollweide(longitude, latitude) {
  let low = -Math.PI / 2;
  let high = Math.PI / 2;
  const target = Math.PI * Math.sin(latitude);
  for (let i = 0; i < 40; i++) {
    const theta = (low + high) / 2;
    if (2 * theta + Math.sin(2 * theta) < target) low = theta;
    else high = theta;
  }
  const theta = (low + high) / 2;
  return [longitude / Math.PI * Math.cos(theta), Math.sin(theta)];
}

export function sourcePixel(longitude, latitude, bounds) {
  const [x, y] = mollweide(longitude, latitude);
  const [left, top, right, bottom] = bounds;
  // A slight inset avoids the JPEG's black frame contaminating the seam and poles.
  return [(left + right) / 2 + x * (right - left) * 0.495,
          (top + bottom) / 2 - y * (bottom - top) * 0.495];
}

export function reproject(image, bounds, width = 1024) {
  const input = document.createElement('canvas');
  input.width = image.naturalWidth;
  input.height = image.naturalHeight;
  const context = input.getContext('2d', { willReadFrequently: true });
  context.drawImage(image, 0, 0);
  const pixels = context.getImageData(0, 0, input.width, input.height).data;
  const output = document.createElement('canvas');
  output.width = width;
  output.height = width / 2;
  const result = output.getContext('2d');
  const buffer = result.createImageData(output.width, output.height);
  for (let row = 0; row < output.height; row++) {
    const latitude = Math.PI / 2 - (row + 0.5) / output.height * Math.PI;
    const [scale, vertical] = mollweide(Math.PI, latitude);
    const [left, top, right, bottom] = bounds;
    const sy = (top + bottom) / 2 - vertical * (bottom - top) * 0.495;
    for (let col = 0; col < output.width; col++) {
      const x = (col + 0.5) / output.width * 2 - 1;
      const sx = (left + right) / 2 + x * scale * (right - left) * 0.495;
      const x0 = Math.max(0, Math.min(input.width - 2, Math.floor(sx)));
      const y0 = Math.max(0, Math.min(input.height - 2, Math.floor(sy)));
      const dx = sx - x0, dy = sy - y0;
      const index = (row * output.width + col) * 4;
      for (let channel = 0; channel < 3; channel++) {
        const at = (xx, yy) => pixels[(yy * input.width + xx) * 4 + channel];
        buffer.data[index + channel] =
          at(x0, y0) * (1 - dx) * (1 - dy) + at(x0 + 1, y0) * dx * (1 - dy)
          + at(x0, y0 + 1) * (1 - dx) * dy + at(x0 + 1, y0 + 1) * dx * dy;
      }
      buffer.data[index + 3] = 255;
    }
  }
  result.putImageData(buffer, 0, 0);
  return output;
}


// Equal Earth (Savric, Patterson & Jenny 2018, doi:10.1080/13658816.2018.1504949), the
// polynomial the paper gives. Equal-area like Mollweide, but the pole is a line 59% of the
// equator's width instead of a point, so the high-latitude continents are less squeezed;
// the sheet is 2.055:1 rather than 2:1. Returned normalised: the equator reaches x = 1 and
// the poles y = 1, the convention the shader and the Mollweide code share.
const EE = [1.340264, -0.081106, 0.000893, 0.003796];
const EE_ROOT3 = Math.sqrt(3);
function equalEarthTheta(latitude) {
  return Math.asin(EE_ROOT3 / 2 * Math.sin(latitude));
}
// dy/dtheta, which the paper's x also divides by.
function equalEarthSlope(theta) {
  const t2 = theta * theta;
  return EE[0] + 3 * EE[1] * t2 + 7 * EE[2] * t2 ** 3 + 9 * EE[3] * t2 ** 4;
}
function equalEarthY(theta) {
  const t2 = theta * theta;
  return theta * (EE[0] + EE[1] * t2 + EE[2] * t2 ** 3 + EE[3] * t2 ** 4);
}
export const EQUAL_EARTH_X = 2 * EE_ROOT3 * Math.PI / (3 * EE[0]);        // half-width, at the equator
export const EQUAL_EARTH_Y = equalEarthY(equalEarthTheta(Math.PI / 2));   // half-height, at the poles
// The sheet's half-height when its half-width is 1: the projection's own aspect, not 0.5.
export const EQUAL_EARTH_HALF = EQUAL_EARTH_Y / EQUAL_EARTH_X;

export function equalEarth(longitude, latitude) {
  const theta = equalEarthTheta(latitude);
  const x = 2 * EE_ROOT3 * longitude * Math.cos(theta) / (3 * equalEarthSlope(theta));
  return [x / EQUAL_EARTH_X, equalEarthY(theta) / EQUAL_EARTH_Y];
}
// Undone by Newton on theta, as the paper describes: y is monotonic in theta, so a few
// steps from the value itself converge well inside a texel.
export function equalEarthInverse(x, y) {
  const target = y * EQUAL_EARTH_Y;
  let theta = target;
  for (let i = 0; i < 12; i++) {
    const step = (equalEarthY(theta) - target) / equalEarthSlope(theta);
    theta -= step;
    if (Math.abs(step) < 1e-12) break;
  }
  const sine = 2 * Math.sin(theta) / EE_ROOT3;
  if (Math.abs(sine) > 1) return null;
  const longitude = 3 * x * EQUAL_EARTH_X * equalEarthSlope(theta) / (2 * EE_ROOT3 * Math.cos(theta));
  if (Math.abs(longitude) > Math.PI + 1e-9) return null;
  return [longitude, Math.asin(sine)];
}


// Plane placements for the flat projections, in the same units as the sheet meshes:
// half-width 1, and the half-height each projection's own shape asks for.

export function placeMollweide(longitude, latitude) {
  const [x, y] = mollweide(longitude * Math.PI / 180, latitude * Math.PI / 180);
  return [x, y * 0.5];
}

export function placeEquirectangular(longitude, latitude) {
  return [longitude / 180, latitude / 180];
}

export function placeEqualEarth(longitude, latitude) {
  const [x, y] = equalEarth(longitude * Math.PI / 180, latitude * Math.PI / 180);
  return [x, y * EQUAL_EARTH_HALF];
}


// The placements undone, to read a longitude and latitude back off a sheet; null off the map.

export function unplaceEquirectangular(x, y) {
  return Math.abs(x) <= 1 && Math.abs(y) <= 0.5 ? [x * 180, y * 180] : null;
}

export function unplaceEqualEarth(x, y) {
  if (Math.abs(y) > EQUAL_EARTH_HALF + 1e-9 || Math.abs(x) > 1 + 1e-9) return null;
  const found = equalEarthInverse(x, y / EQUAL_EARTH_HALF);
  return found && [found[0] * 180 / Math.PI, found[1] * 180 / Math.PI];
}

export function unplaceMollweide(x, y) {
  if (Math.abs(y) > 0.5) return null;
  const theta = Math.asin(2 * y);
  const longitude = x / Math.max(Math.cos(theta), 1e-9) * 180;
  if (Math.abs(longitude) > 180) return null;
  return [longitude, Math.asin((2 * theta + Math.sin(2 * theta)) / Math.PI) * 180 / Math.PI];
}

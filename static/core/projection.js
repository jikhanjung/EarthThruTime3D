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


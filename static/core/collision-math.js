// A user-controlled local scenario, NOT a fit to the published mantle geometry.
export function crustState(age, onset = 60, totalShortening = 1000) {
  if (!Number.isFinite(age) || age < 0 || age > 80 || ![50, 60, 65].includes(onset)
      || !Number.isFinite(totalShortening) || totalShortening < 0 || totalShortening > 1200) {
    throw new Error('Invalid crust scenario');
  }
  const originalWidth = 2000, originalThickness = 35;
  const fraction = Math.max(0, Math.min(1, (onset - age) / onset));
  const shortening = totalShortening * fraction;
  const width = originalWidth - shortening;
  const thickness = originalWidth * originalThickness / width;
  const uplift = (thickness - originalThickness) * (3300 - 2800) / 3300;
  return {shortening, width, thickness, uplift, originalWidth, originalThickness};
}

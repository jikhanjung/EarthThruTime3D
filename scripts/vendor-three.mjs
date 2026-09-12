import { copyFile, mkdir } from 'node:fs/promises';
const target = new URL('../static/vendor/three/', import.meta.url);
await mkdir(target, { recursive: true });
for (const [source, name] of [
  ['build/three.module.js', 'three.module.js'],
  ['build/three.core.js', 'three.core.js'],
  ['examples/jsm/controls/OrbitControls.js', 'OrbitControls.js'],
  ['LICENSE', 'LICENSE'],
]) {
  await copyFile(new URL(`../node_modules/three/${source}`, import.meta.url), new URL(name, target));
}

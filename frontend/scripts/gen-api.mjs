/**
 * Regenerate src/api/schema.ts from the running API's OpenAPI document.
 *
 * The API base URL comes from API_URL, VITE_API_BASE_URL or API_PROXY_TARGET,
 * defaulting to http://localhost:8000. Compose sets API_PROXY_TARGET in the web
 * container, so `docker compose exec web npm run gen:api` works unaided.
 *
 * Plain Node so it behaves the same in PowerShell, cmd and a Linux container.
 */
import { spawnSync } from 'node:child_process';

const base = (
  process.env.API_URL ??
  process.env.VITE_API_BASE_URL ??
  process.env.API_PROXY_TARGET ??
  'http://localhost:8000'
)
  .trim()
  .replace(/\/+$/, '');
const out = 'src/api/schema.ts';

console.log(`gen:api  ${base}/openapi.json -> ${out}`);

const result = spawnSync(
  'npx',
  ['openapi-typescript', `${base}/openapi.json`, '-o', out],
  { stdio: 'inherit', shell: process.platform === 'win32' },
);

if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}
process.exit(result.status ?? 1);

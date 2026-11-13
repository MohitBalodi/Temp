/**
 * Regenerate src/api/schema.ts from the running API's OpenAPI document.
 *
 * The API base URL comes from API_URL (or VITE_API_BASE_URL), defaulting to
 * http://localhost:8000. Inside the web container the API is not on localhost:
 *   docker compose exec -e API_URL=http://api:8000 web npm run gen:api
 *
 * Plain Node so it behaves the same in PowerShell, cmd and a Linux container.
 */
import { spawnSync } from 'node:child_process';

const base = (process.env.API_URL ?? process.env.VITE_API_BASE_URL ?? 'http://localhost:8000')
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

// Validate the Expo client against the changed HTTP contract without native credentials.
import { build, transform } from 'esbuild';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';

const result = await build({ entryPoints: ['../mobile/src/api.js'], bundle: true, write: false, format: 'esm',
  plugins: [{ name: 'expo-test-config', setup(b) {
    b.onResolve({ filter: /^expo-constants$/ }, () => ({ path: 'expo-constants', namespace: 'test' }));
    b.onLoad({ filter: /.*/, namespace: 'test' }, () => ({ contents: 'export default {expoConfig:{extra:{apiBaseUrl:"https://test.invalid"}}}' }));
  } }],
});
const { api } = await import(`data:text/javascript;base64,${Buffer.from(result.outputFiles[0].text).toString('base64')}`);
const calls = [];
globalThis.fetch = async (url, options) => {
  calls.push({ url, ...options });
  return { ok: true, json: async () => url.endsWith('/login') ? { token: 'test-token' } : { id: 42 } };
};
await api.login('test@test.invalid', 'test-password');
await api.saveLog({ log_date: '2026-09-13', client_request_id: 'same-attempt', source: 'garmin', external_id: '123' });
await api.patchLog(42, { log_date: '2026-09-13', expected_revision: 1, distance_km: 8 });
await api.review(42);
await api.importActivities([1, 2]);
assert.equal(calls[1].method, 'POST');
assert.equal(calls[2].method, 'PATCH');
assert(calls[2].url.endsWith('/api/workout-logs/42'));
assert(calls.slice(1).every((c) => c.headers.Authorization === 'Bearer test-token'));
assert.equal(calls[3].headers.Accept, 'application/json');
assert.equal(JSON.parse(calls[1].body).external_id, '123');
assert.equal(JSON.parse(calls[2].body).expected_revision, 1);

async function checkSource(dir) {
  for (const item of await fs.readdir(dir, { withFileTypes: true })) {
    const file = path.join(dir, item.name);
    if (item.isDirectory()) await checkSource(file);
    else if (file.endsWith('.js')) await transform(await fs.readFile(file, 'utf8'), { loader: 'jsx' });
  }
}
await checkSource('../mobile/src');
await transform(await fs.readFile('../mobile/App.js', 'utf8'), { loader: 'jsx' });
console.log('PASS Expo auth headers, separate create/edit, revision, external identity, JSON review and JSX syntax');

/* ════════════════════════════════════════════════════════════════════════════
   Publish a built support client to the gyms' bridges.

     node remote-support/client/release.mjs <vitoo-support.exe> [--rev N]

   <vitoo-support.exe> is the artifact of the "Remote support client (Windows)" workflow
   (gh run download <id> -n vitoo-support-windows-x64-rustdesk-<tag>). The version is
   "<upstream tag>-v<rev>" (rev defaults to 1; raise it for an overlay-only change).

   0. refuses unless publish-source.sh already published this version's source (AGPL) and the
      published vitoo/SHA256SUMS match the overlay here
   1. checks the exe against the .sha256 the workflow wrote next to it, if present
   2. signs `vitoo-support\n<platform>\n<sha256>\n<version>` with the BRIDGE release key
      (~/work/Vitoo-secrets/bridge-signing/, override VB_SIGNING_KEY): bridges already
      trust that key, and the first line keeps it from ever passing for a bridge bundle
   3. writes dist/vitoo-support-<version>.exe and dist/support-client-win32.json
   4. prints the scp lines (exe FIRST, manifest LAST); it does not run them
   ════════════════════════════════════════════════════════════════════════════ */
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { clientSignedMessage, verifyClientManifest, RE_CLIENT_VERSION } from '../../bridge/src/remote-support.js';
import { PUBLIC_KEY_PEM } from '../../bridge/src/updater.js';

const here = path.dirname(new URL(import.meta.url).pathname);
const overlay = JSON.parse(fs.readFileSync(path.join(here, 'overlay.json'), 'utf8'));
const exe = process.argv[2];
const revAt = process.argv.indexOf('--rev');
const rev = revAt > 0 ? Number(process.argv[revAt + 1]) : 1;
if (!exe || !fs.existsSync(exe) || !Number.isInteger(rev) || rev < 1) {
  console.error('usage: node remote-support/client/release.mjs <vitoo-support.exe> [--rev N]'); process.exit(2);
}
const version = `${overlay.upstream_tag}-v${rev}`;
if (!RE_CLIENT_VERSION.test(version)) { console.error(`bad version ${version}`); process.exit(2); }

/* AGPL: no client reaches gyms before its Corresponding Source is public (publish-source.sh),
   and the published build inputs must be the ones on this machine. */
const sourceTag = `vitoo-support-${version}`;
const sumsUrl = `https://raw.githubusercontent.com/${overlay.source_repo}/${sourceTag}/vitoo/SHA256SUMS`;
const sums = await fetch(sumsUrl).then((r) => (r.ok ? r.text() : null), () => null);
if (!sums) {
  console.error(`the source of ${version} is not published yet (${sumsUrl}).\nRun first: bash remote-support/client/publish-source.sh --rev ${rev}`);
  process.exit(1);
}
const listed = new Map(sums.trim().split('\n').map((l) => l.match(/^([0-9a-f]{64}) {2}(.+)$/)).filter(Boolean).map((m) => [m[2], m[1]]));
const BUILD_INPUTS = /^(apply\.py|overlay\.json|settings\.json|custom\.txt|assets\/.+)$/;   // what goes into the exe; tooling may change freely
const differs = ['apply.py', 'overlay.json', 'settings.json', 'custom.txt']
  .filter((f) => !listed.has(f))
  .concat([...listed].filter(([f]) => BUILD_INPUTS.test(f)).filter(([f, h]) => !fs.existsSync(path.join(here, f)) || crypto.createHash('sha256').update(fs.readFileSync(path.join(here, f))).digest('hex') !== h).map(([f]) => f));
if (differs.length) { console.error(`the published source of ${version} differs from this overlay: ${differs.join(', ')}`); process.exit(1); }

const platform = 'win32';
const KEY = process.env.VB_SIGNING_KEY || path.join(os.homedir(), 'work', 'Vitoo-secrets', 'bridge-signing', 'bridge-signing-ed25519.pem');
const priv = crypto.createPrivateKey(fs.readFileSync(KEY));
if (String(crypto.createPublicKey(priv).export({ type: 'spki', format: 'pem' })).trim() !== PUBLIC_KEY_PEM.trim()) {
  console.error('this signing key does not match the bridge public key'); process.exit(1);
}

const buf = fs.readFileSync(exe);
if (buf.subarray(0, 2).toString() !== 'MZ') { console.error('not a Windows executable'); process.exit(1); }
const sha256 = crypto.createHash('sha256').update(buf).digest('hex');
const sumFile = `${exe}.sha256`;
if (fs.existsSync(sumFile) && fs.readFileSync(sumFile, 'utf8').split(/\s+/)[0] !== sha256) {
  console.error('the exe does not match the sha256 the build wrote'); process.exit(1);
}
const signature = crypto.sign(null, Buffer.from(clientSignedMessage(platform, sha256, version), 'utf8'), priv).toString('base64');
const manifest = { platform, version, url: `https://vitoo.ir/downloads/vitoo-support-${version}.exe`, sha256, size: buf.length, signature,
  upstream: overlay.upstream_tag, source: `https://github.com/${overlay.source_repo}/tree/${sourceTag}` };
if (!verifyClientManifest(manifest, platform).ok) { console.error('the manifest does not verify with the bridge public key'); process.exit(1); }

const out = path.join(here, 'dist');
fs.mkdirSync(out, { recursive: true });
fs.copyFileSync(exe, path.join(out, `vitoo-support-${version}.exe`));
fs.writeFileSync(path.join(out, `support-client-${platform}.json`), JSON.stringify(manifest, null, 2) + '\n');
const rel = (f) => path.relative(process.cwd(), path.join(out, f));
console.log(`\nVitoo Support ${version} (RustDesk ${overlay.upstream_tag}), ${(buf.length / 1048576).toFixed(1)} MB, sha256 ${sha256.slice(0, 16)}…, signed\n`);
console.log('Upload (exe first, manifest last):\n');
console.log(`  scp ${rel(`vitoo-support-${version}.exe`)} vitoo:/var/www/vitoo/downloads/`);
console.log(`  scp ${rel(`support-client-${platform}.json`)} vitoo:/var/www/vitoo/downloads/`);
console.log('\nCheck afterwards:');
console.log('  curl -s "https://vitoo.ir/api/bridge/support-client?platform=win32"');
console.log(`  curl -sI https://vitoo.ir/downloads/vitoo-support-${version}.exe   # content-length must be ${buf.length}\n`);

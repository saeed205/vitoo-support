/* Sign settings.json into custom.txt, the way RustDesk's own console does (libsodium crypto_sign,
   "combined" mode: the 64-byte Ed25519 signature followed by the JSON, all base64).

     node remote-support/client/sign-config.mjs

   The private key never leaves the release machine (~/work/Vitoo-secrets/rustdesk/client-config-ed25519.pem,
   override with VS_CONFIG_KEY). Its public half is overlay.json's config_signing_key, which apply.py
   compiles into the client in place of RustDesk's key, so only a custom.txt we signed is accepted.
   custom.txt is public data (no secrets in settings.json) and is committed. */
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const here = path.dirname(new URL(import.meta.url).pathname);
const keyFile = process.env.VS_CONFIG_KEY || path.join(os.homedir(), 'work', 'Vitoo-secrets', 'rustdesk', 'client-config-ed25519.pem');
const overlay = JSON.parse(fs.readFileSync(path.join(here, 'overlay.json'), 'utf8'));
const settings = JSON.parse(fs.readFileSync(path.join(here, 'settings.json'), 'utf8'));
delete settings['//'];
for (const k of ['custom-rendezvous-server', 'relay-server']) {
  if (settings['override-settings'][k] !== overlay.server) throw new Error(`${k} must be ${overlay.server}`);
}
if (settings['override-settings'].key !== overlay.server_key) throw new Error('settings key differs from overlay.json server_key');
if (settings['app-name'] !== overlay.app_name) throw new Error('app-name differs from overlay.json');

const priv = crypto.createPrivateKey(fs.readFileSync(keyFile));
const pub = crypto.createPublicKey(priv).export({ type: 'spki', format: 'der' }).subarray(-32).toString('base64');
if (pub !== overlay.config_signing_key) throw new Error('this key is not overlay.json config_signing_key');

const msg = Buffer.from(JSON.stringify(settings), 'utf8');
const sig = crypto.sign(null, msg, priv);
const out = Buffer.concat([sig, msg]).toString('base64');
/* verify as the client will: split, check against the public key from overlay.json */
const raw = Buffer.from(out, 'base64');
const pubKey = crypto.createPublicKey({ key: Buffer.concat([Buffer.from('302a300506032b6570032100', 'hex'), Buffer.from(overlay.config_signing_key, 'base64')]), format: 'der', type: 'spki' });
if (!crypto.verify(null, raw.subarray(64), pubKey, raw.subarray(0, 64))) throw new Error('self-check failed');
fs.writeFileSync(path.join(here, 'custom.txt'), out);
console.log(`custom.txt signed (${msg.length} bytes of settings)`);

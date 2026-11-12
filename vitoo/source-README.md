# Vitoo Support

**پشتیبانی ویتو** برنامه کوچکی است که باشگاه‌های ویتو با آن به تیم پشتیبانی اجازه می‌دهند صفحه کامپیوترشان را ببیند و کمک کند. هر اتصال فقط با کلیک خود باشگاه پذیرفته می‌شود و باشگاه هر وقت بخواهد آن را می‌بندد.

این برنامه بر پایه [RustDesk](https://github.com/rustdesk/rustdesk) ساخته شده و مثل خود RustDesk تحت مجوز [AGPL-3.0](LICENCE) است. این مخزن سورس کامل هر نسخه‌ای است که به باشگاه‌ها داده می‌شود.

---

**Vitoo Support** is the remote support client that gyms using [Vitoo](https://vitoo.ir) run when they want our support team to see their screen. It only accepts incoming sessions, and each one has to be accepted by a click on the gym's side.

It is [RustDesk](https://github.com/rustdesk/rustdesk) with a small overlay, licensed under [AGPL-3.0](LICENCE) like RustDesk itself. This repository is the Corresponding Source of every build we distribute.

## What is here

| | |
|---|---|
| Tag `vitoo-support-<rustdesk tag>-v<n>` | Exactly the source of that release. Tags are never moved. |
| Branch `vitoo` | The latest release. |
| Everything outside `vitoo/` | RustDesk at the upstream commit named in the release commit, with `vitoo/apply.py` already applied. `libs/hbb_common` is vendored in (it is a submodule upstream) because the overlay edits it. |
| `vitoo/apply.py`, `vitoo/overlay.json` | The overlay: our server and its public key, the key that signs `custom.txt`, product name, version info and icons. It replaces exact strings and stops if upstream changed them. |
| `vitoo/settings.json`, `vitoo/custom.txt` | The built-in settings (incoming only, click to accept, no installation, no RustDesk public servers) and the same settings signed for the client. |
| `vitoo/build-windows.yml` | The GitHub Actions workflow that builds the Windows client. |
| `vitoo/SHA256SUMS` | Checksums of the overlay files. |

## Building

The tree is already patched, so it builds like upstream RustDesk ([build docs](https://rustdesk.com/docs/en/dev/build/)). The release builds use the steps in `vitoo/build-windows.yml`:

1. `python3 build.py --portable --flutter --skip-portable-pack --hwcodec --vram`
2. copy `vitoo/custom.txt` next to the built `rustdesk.exe` and rename the exe to `vitoo-support.exe`
3. pack it with `libs/portable/generate.py`

To point a build at your own server, change `vitoo/overlay.json` on a clean upstream checkout, run `vitoo/apply.py`, and re-sign `vitoo/settings.json` with your own key (`vitoo/sign-config.mjs`). The public half of that key goes in `overlay.json`.

## Credits

RustDesk is Copyright Purslane Tech Pte. Ltd. and its contributors. "RustDesk" is their name; this build is not made or endorsed by them.

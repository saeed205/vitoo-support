#!/usr/bin/env python3
"""Apply Vitoo's overlay to a clean RustDesk checkout (docs/remote-support.md, "the client").

    python3 apply.py <rustdesk checkout> [--check]

Every change is an exact text replacement that must match the expected number of
times, or the script stops with the file and the pattern. That is the point: when
upstream moves code around, the build fails loudly on the first line that no
longer fits, instead of quietly shipping a client that talks to RustDesk's own
servers (the failure mode of sed-based generators). --check only reports.

What it changes, and nothing else:
  1. the built-in rendezvous server and its public key  -> our server (libs/hbb_common config.rs)
  2. the key custom.txt must be signed with             -> our config-signing key (src/common.rs)
  3. the API fallback (admin.rustdesk.com)              -> empty: the client never calls RustDesk's API
  4. product name, company, copyright line, exe names   -> Vitoo (RustDesk's copyright kept beside ours)
  5. icons                                              -> the Vitoo mark (assets/ in this folder)
  6. the incoming-only home window: no empty password row (we accept by click only), a tip
     that says so, our name in the title bar
  7. custom.txt (signed settings, see settings.json)    -> copied next to the exe by the workflow
Settings (incoming only, click to accept, no install, no settings page...) are NOT
patched in: they live in the signed custom.txt, upstream's own mechanism.
"""
import json
import pathlib
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
CFG = json.loads((HERE / "overlay.json").read_text(encoding="utf-8"))

SERVER = CFG["server"]
SERVER_KEY = CFG["server_key"]
CONFIG_KEY = CFG["config_signing_key"]
APP = CFG["app_name"]
PRODUCT = CFG["product_name"]
COMPANY = CFG["company"]
COPYRIGHT = CFG["copyright"]
EXE = CFG["exe_name"]

UP_SERVER = 'pub const RENDEZVOUS_SERVERS: &[&str] = &["rs-ny.rustdesk.com"];'
UP_KEY = 'pub const RS_PUB_KEY: &str = "OeVuKk5nlHiXp+APNn0Y3pC1Iwpwn44JGqrQCsWqmBw=";'
UP_CONFIG_KEY = 'const KEY: &str = "5Qbwsde3unUcJBtrx9ZkvUmwFNoExHzpryHuPUdqlWM=";'
UP_COPYRIGHT = "Copyright © 2026 Purslane Tech Pte. Ltd. All rights reserved."
TITLE_FA = "پشتیبانی ویتو"
TIP_FA = "وقتی پشتیبان ویتو بخواهد وصل شود، پنجره‌ای باز می‌شود و تا شما نپذیرید کسی وارد نمی‌شود"   # no final period: the paragraph is laid out LTR and it would jump to the start of the line
TIP_EN = "When Vitoo support asks to connect, a window opens, and nobody gets in until you accept."

# (file, old, new, expected count). count=None: at least once.
EDITS = [
    ("libs/hbb_common/src/config.rs", UP_SERVER, f'pub const RENDEZVOUS_SERVERS: &[&str] = &["{SERVER}"];', 1),
    ("libs/hbb_common/src/config.rs", UP_KEY, f'pub const RS_PUB_KEY: &str = "{SERVER_KEY}";', 1),
    ("src/common.rs", UP_CONFIG_KEY, f'const KEY: &str = "{CONFIG_KEY}";', 1),
    ("src/common.rs", '    "https://admin.rustdesk.com".to_owned()\n}', '    "".to_owned()\n}', 1),
    # exe metadata (Cargo.toml [package.metadata.winres]) of the app and of the portable packer
    ("Cargo.toml", 'description = "RustDesk Remote Desktop"', f'description = "{PRODUCT}"', 1),
    ("Cargo.toml", f'LegalCopyright = "{UP_COPYRIGHT}"', f'LegalCopyright = "{COPYRIGHT}"', 1),
    ("Cargo.toml", 'ProductName = "RustDesk"', f'ProductName = "{PRODUCT}"', 1),
    ("Cargo.toml", 'FileDescription = "RustDesk Remote Desktop"', f'FileDescription = "{PRODUCT}"', 1),
    ("Cargo.toml", 'OriginalFilename = "rustdesk.exe"', f'OriginalFilename = "{EXE}"', 1),
    ("libs/portable/Cargo.toml", 'description = "RustDesk Remote Desktop"', f'description = "{PRODUCT}"', 1),
    ("libs/portable/Cargo.toml", f'LegalCopyright = "{UP_COPYRIGHT}"', f'LegalCopyright = "{COPYRIGHT}"', 1),
    ("libs/portable/Cargo.toml", 'ProductName = "RustDesk"', f'ProductName = "{PRODUCT}"', 1),
    ("libs/portable/Cargo.toml", 'OriginalFilename = "rustdesk.exe"', f'OriginalFilename = "{EXE}"', 1),
    ("libs/portable/Cargo.toml", 'FileDescription = "RustDesk Remote Desktop"', f'FileDescription = "{PRODUCT}"', 1),
    # where the portable packer unpacks itself (%LOCALAPPDATA%\<prefix>...)
    ("libs/portable/src/main.rs", 'const APP_PREFIX: &str = "rustdesk";', f'const APP_PREFIX: &str = "{APP.lower()}";', 1),
    # the window's version resource
    ("flutter/windows/runner/Runner.rc", 'VALUE "CompanyName", "Purslane Tech Pte. Ltd." "\\0"', f'VALUE "CompanyName", "{COMPANY}" "\\0"', 1),
    ("flutter/windows/runner/Runner.rc", 'VALUE "FileDescription", "RustDesk Remote Desktop" "\\0"', f'VALUE "FileDescription", "{PRODUCT}" "\\0"', 1),
    ("flutter/windows/runner/Runner.rc", 'VALUE "InternalName", "rustdesk" "\\0"', f'VALUE "InternalName", "{APP.lower()}" "\\0"', 1),
    ("flutter/windows/runner/Runner.rc", f'VALUE "LegalCopyright", "{UP_COPYRIGHT}" "\\0"', f'VALUE "LegalCopyright", "{COPYRIGHT}" "\\0"', 1),
    ("flutter/windows/runner/Runner.rc", 'VALUE "OriginalFilename", "rustdesk.exe" "\\0"', f'VALUE "OriginalFilename", "{EXE}" "\\0"', 1),
    ("flutter/windows/runner/Runner.rc", 'VALUE "ProductName", "RustDesk" "\\0"', f'VALUE "ProductName", "{PRODUCT}" "\\0"', 1),
    # home window: approve-mode=click means there is no password, so drop its (empty) row
    ("flutter/lib/desktop/pages/desktop_home_page.dart",
     "    final showOneTime = model.approveMode != 'click' &&\n        model.verificationMethod != kUsePermanentPassword;\n",
     "    final showOneTime = model.approveMode != 'click' &&\n        model.verificationMethod != kUsePermanentPassword;\n"
     "    if (model.approveMode == 'click') return const SizedBox.shrink(); // Vitoo: accept by click only\n", 1),
    # ...and the tip under «Your Desktop» stops talking about a password
    ("src/lang/fa.rs", '("desk_tip", "دسکتاپ شما با این شناسه و رمز عبور قابل دسترسی است"),', f'("desk_tip", "{TIP_FA}"),', 1),
    ("src/lang/en.rs", '("desk_tip", "Your desktop can be accessed with this ID and password."),', f'("desk_tip", "{TIP_EN}"),', 1),
    # title bar: our name beside the icon (upstream shows the icon alone, or a hard-coded "RustDesk")
    ("flutter/lib/desktop/widgets/tabbar_widget.dart", "offstage: !showTitle,", "offstage: !showTitle && !bind.isIncomingOnly(),", 1),
    ("flutter/lib/desktop/widgets/tabbar_widget.dart", 'child: const Text(\n                              "RustDesk",',
     f'child: Text(\n                              bind.isIncomingOnly() ? "{TITLE_FA}" : "RustDesk",', 1),
]

# (source in assets/, destination in the checkout). Each destination must already exist upstream.
ICONS = [
    ("icon.ico", "res/icon.ico"),
    ("icon.ico", "res/tray-icon.ico"),
    ("icon.ico", "flutter/windows/runner/resources/app_icon.ico"),
    ("icon-512.png", "res/icon.png"),
    ("icon-32.png", "res/32x32.png"),
    ("icon-64.png", "res/64x64.png"),
    ("icon-128.png", "res/128x128.png"),
    ("icon-256.png", "res/128x128@2x.png"),
    ("icon.svg", "flutter/assets/icon.svg"),
]

# (source in assets/, destination) for files upstream does NOT have; if upstream adds one, we stop.
NEW_ASSETS = [
    # the 16 px title-bar icon: loadIcon() tries assets/icon.png before icon.svg, and our svg
    # came out as loose coloured dots at that size (seen on Windows, 2026-11-01)
    ("icon-128.png", "flutter/assets/icon.png"),
]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check = "--check" in sys.argv
    if len(args) != 1:
        sys.exit(__doc__)
    root = pathlib.Path(args[0]).resolve()
    bad = []
    pending = {}
    for rel, old, new, want in EDITS:
        p = root / rel
        if not p.is_file():
            bad.append(f"{rel}: file not found")
            continue
        # bytes as they are (a Windows checkout has CRLF): patterns follow the file's line ends
        text = pending.get(rel) or p.read_bytes().decode("utf-8")
        if "\r\n" in text:
            old, new = old.replace("\n", "\r\n"), new.replace("\n", "\r\n")
        n = text.count(old)
        if (want is None and n < 1) or (want is not None and n != want):
            bad.append(f"{rel}: expected {want} of {old!r}, found {n}")
            continue
        pending[rel] = text.replace(old, new)
    for src, dst in ICONS:
        if not (HERE / "assets" / src).is_file():
            bad.append(f"assets/{src}: missing in the overlay")
        if not (root / dst).is_file():
            bad.append(f"{dst}: upstream no longer has this icon")
    for src, dst in NEW_ASSETS:
        if not (HERE / "assets" / src).is_file():
            bad.append(f"assets/{src}: missing in the overlay")
        if (root / dst).exists():
            bad.append(f"{dst}: upstream has this file now, check it before replacing")
    if bad:
        print("The overlay no longer fits this RustDesk version:\n  " + "\n  ".join(bad))
        sys.exit(1)
    if check:
        print(f"overlay fits: {len(EDITS)} edits, {len(ICONS) + len(NEW_ASSETS)} icons")
        return
    for rel, text in pending.items():
        (root / rel).write_bytes(text.encode("utf-8"))
    for src, dst in ICONS + NEW_ASSETS:
        shutil.copyfile(HERE / "assets" / src, root / dst)
    print(f"overlay applied: {len(EDITS)} edits in {len(pending)} files, {len(ICONS) + len(NEW_ASSETS)} icons, server {SERVER}")


if __name__ == "__main__":
    main()

#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
# Publish the Corresponding Source of a support client release (AGPL-3.0, sections 6 and 13).
#
#   bash remote-support/client/publish-source.sh [--rev N] [--dry-run]
#
# The public repository (overlay.json "source_repo", a GitHub fork of rustdesk/rustdesk) gets:
#   - branch `vitoo`: upstream at overlay.json "upstream_commit", with apply.py already applied,
#     libs/hbb_common vendored in (our patch edits it, and a submodule pointer cannot carry that),
#     and this overlay folder copied to vitoo/ (with SHA256SUMS of every file)
#   - tag `vitoo-support-<upstream tag>-v<rev>`: the same commit, never moved afterwards
#
# release.mjs refuses to sign a version whose tag is missing or whose published vitoo/SHA256SUMS
# differ from the local overlay, so a client never reaches gyms without its source online.
# Nothing secret is in this folder: the signing keys live in ~/work/Vitoo-secrets/ only.
# ════════════════════════════════════════════════════════════════════════════
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
rev=1; dry=0
while [ $# -gt 0 ]; do
  case $1 in
    --rev) rev=$2; shift 2 ;;
    --dry-run) dry=1; shift ;;
    *) echo "usage: bash publish-source.sh [--rev N] [--dry-run]" >&2; exit 2 ;;
  esac
done
[[ $rev =~ ^[1-9][0-9]*$ ]] || { echo "bad --rev $rev" >&2; exit 2; }
j() { python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])' "$here/overlay.json" "$1"; }
tag=$(j upstream_tag); commit=$(j upstream_commit); repo=$(j source_repo)
version="$tag-v$rev"; rtag="vitoo-support-$version"
url="https://github.com/$repo"

if git ls-remote --exit-code "$url" "refs/tags/$rtag" >/dev/null 2>&1; then
  echo "$rtag is already published at $url; raise --rev for a new overlay" >&2; exit 1
fi

work=$(mktemp -d); trap 'rm -rf "$work"' EXIT
echo "== $repo: upstream $tag ($commit), release $version"
git clone -q --filter=blob:none --no-checkout "$url" "$work/src"
cd "$work/src"
git fetch -q https://github.com/rustdesk/rustdesk "$commit"
git checkout -q -B vitoo "$commit"
git submodule update -q --init libs/hbb_common

python3 -I "$here/apply.py" .

# vendor hbb_common: drop the gitlink and the .gitmodules entry, add its files
sub=$(git -C libs/hbb_common rev-parse HEAD)
rm -rf libs/hbb_common/.git .git/modules/libs/hbb_common
git rm -q --cached libs/hbb_common
git config -f .gitmodules --remove-section submodule.libs/hbb_common
[ -s .gitmodules ] || git rm -q -f .gitmodules

mkdir -p vitoo
(cd "$here" && git ls-files -z . | xargs -0 tar cf -) | tar xf - -C vitoo     # committed files only
cp "$here/../../.github/workflows/remote-support-client.yml" vitoo/build-windows.yml
cp "$here/source-README.md" README.md
(cd vitoo && find . -type f ! -name SHA256SUMS ! -name build-windows.yml | LC_ALL=C sort | sed 's|^\./||' | xargs shasum -a 256 > SHA256SUMS)

git add -A
git -c user.name="Vitoo" -c user.email="support@vitoo.ir" commit -q -m "Vitoo Support $version

RustDesk $tag ($commit) with the Vitoo overlay applied (vitoo/apply.py),
libs/hbb_common vendored from rustdesk/hbb_common $sub.
Licensed under AGPL-3.0 like RustDesk; see LICENCE."
git tag -a "$rtag" -m "Vitoo Support $version (RustDesk $tag)"
git log --oneline -1 --stat | tail -3

if [ $dry = 1 ]; then echo "dry run: nothing pushed"; exit 0; fi
git push -q --force origin vitoo
git push -q origin "refs/tags/$rtag"
echo "published $url/tree/$rtag"

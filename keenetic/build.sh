#!/usr/bin/env bash
# Cross-builds amneziawg-go (patched to drop IFF_VNET_HDR, see
# tun-no-vnet-hdr.patch) for Keenetic/Entware targets: aarch64 (Netcraze,
# linux/arm64), mipsel and mips (older Keenetic hardware, GOMIPS=softfloat).
#
# Usage: keenetic/build.sh
# Env:
#   AWG_VERSION   go module version to fetch (default: v3.1.20260814)
#   TARGETS       space-separated subset of "aarch64 mipsel mips" (default: all)
#   NO_PATCH=1    skip applying tun-no-vnet-hdr.patch
set -euo pipefail

AWG_VERSION="${AWG_VERSION:-v3.1.20260814}"
MODULE="github.com/amnezia-vpn/amneziawg-go/v3"
TARGETS="${TARGETS:-aarch64 mipsel mips}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PATCH_FILE="$SCRIPT_DIR/tun-no-vnet-hdr.patch"
DIST_DIR="$REPO_ROOT/dist"

# suffix -> "GOOS GOARCH GOMIPS" (GOMIPS empty where not applicable)
target_env() {
	case "$1" in
	aarch64) echo "linux arm64" ;;
	mipsel) echo "linux mipsle softfloat" ;;
	mips) echo "linux mips softfloat" ;;
	*)
		echo "unknown target: $1 (want: aarch64 mipsel mips)" >&2
		exit 1
		;;
	esac
}

sha256() {
	if command -v sha256sum >/dev/null 2>&1; then
		sha256sum "$1"
	else
		shasum -a 256 "$1"
	fi
}

mkdir -p "$DIST_DIR"

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

echo "==> fetching $MODULE@$AWG_VERSION"
(
	cd "$WORKDIR"
	go mod init tmp-awg-build >/dev/null
	go get "${MODULE}@${AWG_VERSION}"
)

MOD_DIR="$(cd "$WORKDIR" && go list -m -f '{{.Dir}}' "$MODULE")"
[ -n "$MOD_DIR" ] && [ -d "$MOD_DIR" ] || {
	echo "could not resolve module dir for $MODULE@$AWG_VERSION" >&2
	exit 1
}

SRC_DIR="$WORKDIR/src"
echo "==> copying module source ($MOD_DIR -> $SRC_DIR)"
cp -R "$MOD_DIR" "$SRC_DIR"
chmod -R u+w "$SRC_DIR"

if [ "${NO_PATCH:-0}" = "1" ]; then
	echo "==> NO_PATCH=1, skipping tun-no-vnet-hdr.patch"
else
	echo "==> applying tun-no-vnet-hdr.patch"
	(cd "$SRC_DIR" && patch -p1 <"$PATCH_FILE")
fi

SUMS_FILE="$DIST_DIR/SHA256SUMS"
: >"$SUMS_FILE.tmp"

for suffix in $TARGETS; do
	# shellcheck disable=SC2046 # word-splitting the "GOOS GOARCH GOMIPS" triple is intended
	set -- $(target_env "$suffix")
	goos="$1" goarch="$2" gomips="${3:-}"
	out="$DIST_DIR/amneziawg-go-${AWG_VERSION}-${suffix}"

	echo "==> building $suffix ($goos/$goarch${gomips:+ GOMIPS=$gomips}) -> $out"
	(
		cd "$SRC_DIR"
		export CGO_ENABLED=0 GOOS="$goos" GOARCH="$goarch"
		[ -n "$gomips" ] && export GOMIPS="$gomips"
		go build -trimpath -ldflags="-s -w" -o "$out" .
	)
	(cd "$DIST_DIR" && sha256 "$(basename "$out")") >>"$SUMS_FILE.tmp"
done

mv "$SUMS_FILE.tmp" "$SUMS_FILE"

echo "==> done"
ls -l "$DIST_DIR"

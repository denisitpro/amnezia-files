# amnezia-files

Patched builds of upstream [amneziawg-go](https://github.com/amnezia-vpn/amneziawg-go)
for Keenetic routers, plus the Entware scripts to run AmneziaWG (AWG 3.1) as a
userspace tunnel on `OpkgTun` interfaces.

## Download

Stable URLs that always point at the latest published release
(`.../releases/latest/download/<name>`):

| File | Target |
|---|---|
| `amneziawg-go-linux-aarch64` | linux/arm64 (Netcraze and similar) |
| `amneziawg-go-linux-mipsel` | linux/mipsle (softfloat) |
| `amneziawg-go-linux-mips` | linux/mips (softfloat) |
| `SHA256SUMS` | checksums for all release assets |
| `LICENSE-amneziawg-go` | upstream license (MIT), ships with every release |

Base URL: `https://github.com/denisitpro/amnezia-files/releases/latest/download/`

Verify with `sha256sum -c SHA256SUMS`.

## The patch

`keenetic/tun-no-vnet-hdr.patch` drops `IFF_VNET_HDR` from the TUN open in
`tun/tun_linux.go` (one line), for Keenetic's old 4.9-ndm kernel. This is the
build that runs in production on a Netcraze NC-1812. An unpatched build also
starts there, but was not compared against the patched one over time.

## Building locally

Requires Go (`stable`): `keenetic/build.sh`

Default upstream version is in `version.txt` at the repo root.

Env vars:

- `AWG_VERSION` — module version to fetch (default: contents of `version.txt`)
- `TARGETS` — subset of `aarch64 mipsel mips` (default: all)
- `NO_PATCH=1` — skip applying the patch

Output goes to `dist/`.

## Cutting a release

A push to `main` builds and publishes the `keenetic-<version>` release (version
from `version.txt`) and marks it latest. You can also run Actions → Build →
Run workflow: leave `awg_version` empty to use `version.txt`, or override it;
leave `publish` checked. Pull requests only build and lint.

## Scripts (also published as release assets)

- `scripts/conf2uapi.py` — wg-quick `.conf` → amneziawg-go UAPI `set` request
- `scripts/S99awg` — Entware init script (start/stop/restart/status)
- `scripts/awg-v6block` — rejects IPv6 on tunnel-routed ndm policies
- `scripts/50-awg-v6.sh` — ndm hook re-applying `awg-v6block`

## License

Binaries are built from [amnezia-vpn/amneziawg-go](https://github.com/amnezia-vpn/amneziawg-go)
(MIT); its notice ships as `LICENSE-amneziawg-go` in every release. This
repository itself currently has no LICENSE file.

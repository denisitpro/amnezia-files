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

Keenetic's 4.9-ndm kernel doesn't support `IFF_VNET_HDR` on its `tun` driver,
so upstream's TUN-up detection hack fails to bring the interface up;
`keenetic/tun-no-vnet-hdr.patch` drops that flag in `tun/tun_linux.go`.

## Building locally

Requires Go (`stable`): `keenetic/build.sh`

Env vars:

- `AWG_VERSION` — module version to fetch (default `v3.1.20260814`)
- `TARGETS` — subset of `aarch64 mipsel mips` (default: all)
- `NO_PATCH=1` — skip applying the patch

Output goes to `dist/`.

## Cutting a release

Actions → Build → Run workflow → set `awg_version`, leave `publish` checked.
Builds all targets, then creates/updates the `keenetic-<awg_version>` release
and marks it latest. A plain push or pull request only builds and lints.

## Scripts (also published as release assets)

- `scripts/conf2uapi.py` — wg-quick `.conf` → amneziawg-go UAPI `set` request
- `scripts/S99awg` — Entware init script (start/stop/restart/status)
- `scripts/awg-v6block` — rejects IPv6 on tunnel-routed ndm policies
- `scripts/50-awg-v6.sh` — ndm hook re-applying `awg-v6block`

## License

Binaries are built from [amnezia-vpn/amneziawg-go](https://github.com/amnezia-vpn/amneziawg-go)
(MIT); its notice ships as `LICENSE-amneziawg-go` in every release. This
repository itself currently has no LICENSE file.

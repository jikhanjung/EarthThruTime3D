# Operations status

Deployed since 2026-09-12 at https://earththrutime.nopeoplestime.info/ on the dolfinid
host. Configuration and procedure live in `deploy/README.md` and `deploy/deploy.toml`.
Builds happen on the development host; the server only loads the image and swaps.
The shared guides are referenced privately through `.guides`; they are not copied.

Current release: **v0.22.0**, deployed 2026-09-24 (Asia/Seoul). The projection picker
gains Equal Earth (PR #86): equal-area like Mollweide but with a pole line 59% of the
equator's width, so the high-latitude ice sheets are not squeezed into a wedge; its sheet
is 2.055:1, the one flat mesh that is not the 2:1 box. Code only: the runtime bundle is
the 1,288 files (482,280,982 bytes) of v0.20.0 and v0.21.0, byte-identical. Location pins
(v0.21.0), the modelled climate (v0.20.0) and the PaleoMIST ice (v0.19.0) are as before;
the crustal depression is still not drawn (#59 step c, planned in P08).
Image/data hashes, DB backup and public verification are in
[devlog 106](../devlog/20260924_jikhanjung_106_release_0220.md).
Browser transfer measurements and the ice-river data generation are recorded in
[devlog 079](../devlog/20260916_jikhanjung_079_release_0140.md).

On 2026-09-18, old project releases were pruned with `KEEP=2`: v0.18.1 and
v0.18.0 remained available (v0.19.0 and v0.20.0 have since been added). On 2026-09-20 the same `KEEP=2` prune removed
v0.18.0 and v0.18.1 (+1,784 MiB, 13 GiB free, 79% used); v0.22.0 now runs, with v0.21.0 and v0.20.0 kept as
rollbacks ([devlog 104](../devlog/20260920_jikhanjung_104_dolfinid_prune_0200.md)). Eleven old releases were removed, reclaiming 8,099 MiB;
the host had 16.4 GiB free (72% used) immediately afterwards. No database, backups,
secrets or other projects were pruned. See
[devlog 099](../devlog/20260918_jikhanjung_099_dolfinid_release_cleanup.md).

## Adopted now

- Django 5.2 dependencies pinned; separate development and production settings.
- Production rejects missing/weak secrets, wildcard hosts and implicit DB paths.
- Production HTTPS and secure-cookie defaults; forwarding-header trust is opt-in.
- Admin access requires an active staff superuser. No automatic password bootstrap.
- Data, uploads, environment files and private guides excluded from Git.
- Shared PaleoBytes footer, version metadata, About/privacy/contact pages.
- Offsite backup, daily at 04:20 on the m710q development host
  (`system-operation/m710q/backup-earththrutime.sh`): the newest verified hourly DB
  snapshot and `.env.django` are pulled from dolfinid and kept by date (30 days locally,
  90 on the NAS, month-starts and 1 December for ever), and the development host's
  `data/sources` and the newest release bundle are mirrored to the NAS, while
  `data/derived` is kept as `rsync --link-dest` snapshots (daily for 14 days, weekly for
  12 weeks, monthly for 12 months and every December for ever) mirrored to the NAS with
  hard links preserved. The data is files, not rows, and is made on the development host, so the mirror
  runs from there rather than from the server. Sessions are not stripped from the
  snapshot: the database has no user accounts, only the administrator's.
- Licence: MIT for the code (`LICENSE`), CC BY 4.0 for the data derived from CC BY
  sources, the unsettled masks under their sources' terms (`LICENSE-DATA.md`).
- `/healthz`: `ok`/200 requires a reachable database with migration history and, when
  the viewer is enabled, every field in the configured default surface series. The
  deployed default is `paleoatlas2016`: 90 expected fields. Missing DB/schema or required
  fields yields `unhealthy`/503; an `INTEGRITY_FAIL` sentinel after those checks pass
  yields `degraded`/200. The JSON includes source, expected count and missing count.
  This is an existence check, not a per-request integrity scan or a full check of
  optional climate, ice and plate layers. Bundle hashes are checked at startup.
- Seed: **(none)**. Geological assets are files described by provenance manifests,
  not database seed rows. The domain invariant is already implemented as default-series
  field completeness; the database stores Django administrative/session state.

## Adopted at the 2026-09-12 deployment

- Verbs under standard names: `preflight`/`build`, `deploy`, `smoke`, `rollback`,
  `backup`. `seed` is still **(none)**. Preflight runs Django's checks, the
  missing-migration check and the test suite before any image is built.
- Smoke requires status `ok`, the expected version, and the domain invariant: every
  derived land field of the default mask source present (17 at the first deployment,
  90 since the 2016 PaleoAtlas became the default). `smoke.sh` resolves the published
  port through `docker compose config --format json` and checks the health JSON and
  version; it does not fetch every field URL. Image/browser checks cover serving.
- Rollback is the deploy command with the previous version, exercised in both
  directions on the day of the first deployment.
- Build happens on the development host. The server loads an immutable versioned image
  and swaps; it never builds.
- Non-root container (UID 10001), read-only root filesystem, `/tmp` on tmpfs, all
  capabilities dropped, `no-new-privileges`, port bound to `127.0.0.1:8014` only, host
  nginx terminating TLS with Let's Encrypt and webroot renewal.
- Collectstatic runs at build time because the running root filesystem is read-only.
  Migrations run at container startup against the persistent DB volume. The host never
  migrates a running database.
- The image and its data bundle are validated as a pair before the running service is
  touched: the manifest version must match the image and every file's size and SHA-256
  must match. A mismatched pair refuses to start.
- Pre-deploy and hourly snapshots, taken with sqlite3's backup API from a throwaway
  container, integrity-checked, and discarded if the check fails. Pruning happens only
  after a verified new snapshot exists and never below one kept copy.
- Code rollback and data restore stay separate: no deploy path writes to `db/`.
- Secrets are provisioned in `.env.django` on the host at 600, never in the image.
- The PALEOMAP originals are excluded from the image, the bundle and the server. The
  build fails if a JPEG appears in the image, and the running container is checked for
  refusing to serve one.

## Still outstanding

- **Restore drill.** Rollback of code is exercised; restoring a database from a snapshot
  has not been rehearsed. The database holds only administrator accounts and sessions,
  so this waits until it holds something a reader would miss.
- **Disk monitoring and backup-failure alerting.** The host was at 89% when the service
  was installed. A failed hourly snapshot is visible in the journal but nothing raises it.
- **Social preview metadata and a touch icon.** The shell has a favicon only.
- HSTS stays at one day with subdomain inclusion and preload off, which `check --deploy`
  reports as two warnings. That is deliberate until the domain set is settled.

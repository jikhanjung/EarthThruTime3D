# Operations status

Deployed since 2026-09-12 at https://earththrutime.nopeoplestime.info/ on the dolfinid
host. Configuration and procedure live in `deploy/README.md` and `deploy/deploy.toml`.
Builds happen on the development host; the server only loads the image and swaps.
The shared guides are referenced privately through `.guides`; they are not copied.

## Adopted now

- Django 5.2 dependencies pinned; separate development and production settings.
- Production rejects missing/weak secrets, wildcard hosts and implicit DB paths.
- Production HTTPS and secure-cookie defaults; forwarding-header trust is opt-in.
- Admin access requires an active staff superuser. No automatic password bootstrap.
- Data, uploads, environment files and private guides excluded from Git.
- Shared PaleoBytes footer, version metadata, About/privacy/contact pages.
- Licence: MIT for the code (`LICENSE`), CC BY 4.0 for the data derived from CC BY
  sources, the unsettled masks under their sources' terms (`LICENSE-DATA.md`).
- `/healthz`: `ok`/200 for a reachable database with migration history,
  `unhealthy`/503 if unavailable/uninitialized, `degraded`/200 if an
  `INTEGRITY_FAIL` sentinel exists beside the database. No expensive integrity scan.
- Seed: **(none)**. No geological records exist yet; schema readiness is the temporary
  health invariant. Replace it with a meaningful domain invariant once data exists.

## Adopted at the 2026-09-12 deployment

- Verbs under standard names: `preflight`/`build`, `deploy`, `smoke`, `rollback`,
  `backup`. `seed` is still **(none)**. Preflight runs Django's checks, the
  missing-migration check and the test suite before any image is built.
- Smoke requires status `ok`, the expected version, and the domain invariant: every
  derived land field of the default mask source present and served (17 at the first
  deployment, 90 since the 2016 PaleoAtlas became the default).
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

- **Offsite backups.** Pre-deploy and hourly snapshots exist on the same host. No
  offsite destination has been chosen, so the session-clearing and VACUUM steps that
  belong to an offsite copy are not implemented either.
- **Restore drill.** Rollback of code is exercised; restoring a database from a snapshot
  has not been rehearsed.
- **Disk monitoring and backup-failure alerting.** The host was at 89% when the service
  was installed. A failed hourly snapshot is visible in the journal but nothing raises it.
- **Social preview metadata and a touch icon.** The shell has a favicon only.
- HSTS stays at one day with subdomain inclusion and preload off, which `check --deploy`
  reports as two warnings. That is deliberate until the domain set is settled.

# Operations status

This is a local development scaffold, not a configured production deployment.
No production host, registry, domain, container stack or backup destination exists here.
The shared guides are referenced privately through `.guides`; they are not copied.

## Adopted now

- Django 5.2 dependencies pinned; separate development and production settings.
- Production rejects missing/weak secrets, wildcard hosts and implicit DB paths.
- Production HTTPS and secure-cookie defaults; forwarding-header trust is opt-in.
- Admin access requires an active staff superuser. No automatic password bootstrap.
- Data, uploads, environment files and private guides excluded from Git.
- Shared PaleoBytes footer, version metadata, About/privacy/contact pages.
- `/healthz`: `ok`/200 for a reachable database with migration history,
  `unhealthy`/503 if unavailable/uninitialized, `degraded`/200 if an
  `INTEGRITY_FAIL` sentinel exists beside the database. No expensive integrity scan.
- Seed: **(none)**. No geological records exist yet; schema readiness is the temporary
  health invariant. Replace it with a meaningful domain invariant once data exists.

## Before production

Implement `preflight`, `deploy`, `seed`, `smoke`, and `rollback` under standard names.
Preflight must inspect migrations, environment/configuration and seed changes against
the prior release. Smoke must require status `ok`, the expected version and a domain
invariant. Deploy and rollback are intentionally not executable placeholders today.

Build/test images off production. Production only pulls immutable versioned images.
Use a non-root container, persistent DB-directory/media mounts, local-only port binding,
and nginx TLS. After stopping all writers, the container startup runs collectstatic,
migrations, and gunicorn. Never migrate a running production DB from the host.

Provide verified pre-deploy, hourly and offsite backups. Verify snapshots before adoption;
never prune on failed/missing sources. Offsite copies must clear sessions and VACUUM
after integrity verification. Restore only after all writers stop; exercise restoration.
Code rollback and data restore must remain separate. Deployment updates the image tag
without replacing credentials or host configuration. Surface backup failures and monitor
disk usage. Do not reseed operator-authored records.

Provision `.env` values explicitly; do not ship secrets in an image. A trusted reverse
proxy must strip incoming forwarding headers before `TRUST_PROXY_HEADERS=true` is set.
Initial HSTS is one day; subdomain inclusion/preload default off until domains are ready.
Run `check --deploy` with production settings. Resolve deployment-specific warnings.
Finalize public contact/privacy details, asset attribution, touch icon and social preview
metadata before publication; the initial shell has a favicon but no social image.

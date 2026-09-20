# Project instructions

- Shared web standards: `.guides/web/README.md`; branding: `.guides/branding.md`.
- `.guides` is a local, gitignored symlink to `../devdocs/guides`. If missing,
  place the private devdocs checkout beside this repository and recreate the link.
  Never copy or commit the private guides. The guide index's no-copy policy takes
  precedence over the older copy instruction in the web adoption checklist.
- Django must stay on the 5.2 release line. Use `.venv/bin/python` explicitly.
- Run `make check` and `make test` for behavior changes.
- Before branching, and again before opening or updating a PR: `git fetch origin`, read
  the commits on `main` since your base and the open PRs and issues, and rebase or merge
  onto `main` first. Several people push to `main` on the same day; a PR that cannot
  merge wastes the reviewer's time.
- Devlogs are named `YYYYMMDD_{author}_{nnn}_{title}.md` with a per-author number (see
  `devlog/README.md`); take your own next number, and add the entry to the index.
- Every PR that changes what the site shows or the data it serves adds an entry to
  `CHANGELOG.md`: what changed, with the PR and devlog linked, and how to see it on screen
  (dataset, time range, stop, control). The release PR gives the pending entries their
  `## vX.Y.Z — date` heading. Docs-only PRs are exempt.
- Keep scientific source observations, interpolated geometry and simulated results
  distinguishable. A 10,000-year display tick is not a claim of scientific accuracy.
- Production runs on the dolfinid host (`deploy/README.md`). Changes to deployment must
  keep the data safety contract and deploy verbs described in `docs/operations.md`.
- Never write a running production SQLite database from the host, replace a live
  database, overwrite production secrets, or mix operational records into seeds.

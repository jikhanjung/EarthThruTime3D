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
  merge wastes the reviewer's time, and devlog numbers are assigned on `main`, so take
  the next free number after fetching, not the next one you remember.
- Keep scientific source observations, interpolated geometry and simulated results
  distinguishable. A 10,000-year display tick is not a claim of scientific accuracy.
- Production is not configured yet. Before adding deployment, implement the data
  safety contract and deploy verbs described in `docs/operations.md`.
- Never write a running production SQLite database from the host, replace a live
  database, overwrite production secrets, or mix operational records into seeds.

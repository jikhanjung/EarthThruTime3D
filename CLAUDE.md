Project instructions are in `AGENTS.md`. Shared web standards are linked at
`.guides/web/README.md` and `.guides/branding.md`. If missing, the sibling private
devdocs checkout is absent or unlinked; never commit the guides into this repository.

## devlog file names

Since 2026-09-14 two people write devlogs, so file names carry the author and a
per-author number: `devlog/YYYYMMDD_{author}_{nnn}_{title}.md` (plans:
`YYYYMMDD_{author}_P{nn}_{title}.md`). `author` is the lowercase GitHub account name
(`jikhanjung`, `wwolf`); `title` is English snake_case. Take the next number of that
author, not of the repository: jikhanjung continues from 046, wwolf starts at 001. Files
001–045 keep their old names. Refer to another devlog by link or as "jikhanjung 046",
and add every new file to the index in `devlog/README.md`.

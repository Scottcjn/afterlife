# Name check (2026-11-06, read-only)

"afterlife" is taken.
- PyPI `afterlife`: exists (HTTP 200, v0.0.1, summary "Coming soon."), so we cannot publish under it.
- GitHub: many repos named afterlife (Inoxoft/afterlife, ad3rito/AfterLife, powerof3/Afterlife, ...). Not blocking
  for a repo under our own org, but confusing in search.

Candidates (PyPI JSON endpoint status; `gh search repos "<n> in:name"`):

| name | PyPI | GitHub |
|---|---|---|
| afterlife-gpu | 404 (free) | no results (free) |
| revenant-gpu | 404 (free) | no results (free) |
| lazarus-gpu | 404 (free) | no results (free) |
| stranded-gpu | 404 (free) | no results (free) |
| strand-gpu | 404 (free) | 1 unrelated research repo |

Chosen: **afterlife-gpu** (distribution name). Keeps the brand and says what it is.
- Repo dir and import package stay `afterlife`; the CLI command stays `afterlife`.
- Caveat: the import name `afterlife` would clash if the unrelated PyPI `afterlife` is installed in the
  same environment. If that matters, rename the import package to `afterlife_gpu` later.
- Availability is a point-in-time check; re-verify immediately before publishing.

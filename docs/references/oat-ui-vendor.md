# Oat UI vendored assets

The site serves Oat UI locally so page rendering does not depend on a third-party
origin. The two bundles are immutable copies of the Oat `gh-pages` publishing
snapshot at commit `3be797d1f56322b213804c76169875a87bab82e0`, retrieved on
2026-08-24.

Upstream repository: <https://github.com/knadh/oat>

Published snapshot:
<https://github.com/knadh/oat/tree/3be797d1f56322b213804c76169875a87bab82e0>

| Local file | Upstream path | Bytes | SHA-256 |
|---|---|---:|---|
| `web/oat.min.css` | `oat.min.css` | 31,581 | `2a24ff15f1e5cd70986eb242d9bbcbd9562b1cd5c039fde8c20955615687d655` |
| `web/oat.min.js` | `oat.min.js` | 10,421 | `f5814e213b82fa4edcff31963917c3bd9493761c5a2e93da2f6998ec9f41815c` |

Oat is distributed under the MIT License. The retained upstream notice is in
`web/oat.LICENSE.txt`. Its source is the Oat v0.7.1 commit
`9fb94e370947f39a9e7bc40d43d15c91a3856f71`.

When updating these files, select an immutable publishing commit, replace both
bundles together, verify their hashes, copy the upstream license verbatim, and
update this record and the cache tag in the same change.

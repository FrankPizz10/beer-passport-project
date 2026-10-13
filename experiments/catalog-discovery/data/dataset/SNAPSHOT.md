# Open Brewery DB dataset snapshot

Used by the catalog-discovery experiment as an alternative to the live
Open Brewery DB API (which returned 403s from both the build environment
and the project owner's machine; precise cause unconfirmed).

- **Repository:** https://github.com/openbrewerydb/openbrewerydb
- **Commit:** `4d33d43af09eac011415eba834cd97fc86b0c99a`
  ("chore: workflow maintain"; dataset actively maintained, e.g. recent
  "data: add Massachusetts breweries" PRs)
- **File:** `breweries.csv` (2.2 MB, 11,959 rows, retrieved 2026-10-12)
- **Download URL:** https://raw.githubusercontent.com/openbrewerydb/openbrewerydb/4d33d43af09eac011415eba834cd97fc86b0c99a/breweries.csv
- **Local path (gitignored, do not commit):**
  `data/dataset/openbrewerydb-breweries.csv`
- **Columns:** id, name, brewery_type, address_1, address_2, address_3,
  city, state_province, postal_code, country, phone, website_url,
  longitude, latitude
- **Attribution:** Producer data: Open Brewery DB (openbrewerydb.org)

## Reuse terms (checked 2026-10-12)

- Repository `LICENSE` is MIT (covers the software and associated
  documentation files).
- The FAQ (https://openbrewerydb.org/faq) governs dataset reuse: "You are
  welcome to use the dataset for any projects with credit to Open Brewery
  DB." The API is described as free, unauthenticated, community-supported
  with no SLAs, recommended for personal projects.
- **Remaining ambiguity:** whether the MIT license's "Software" covers the
  dataset files, and what "credit" concretely requires (attribution text,
  placement). Treat as an open question for production use; fine for this
  experiment with the attribution above recorded in outputs.

To reproduce: download the CSV from the URL above into
`data/dataset/openbrewerydb-breweries.csv`, then run with
`--brewery-source dataset`.

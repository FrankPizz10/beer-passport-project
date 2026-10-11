# Image and catalog data licensing research

- **Date:** October 2026 (from `BeerPassport_2_0_Product_and_Engineering_Plan.docx`, section 5).
- **Question:** Where can BeerPassport lawfully source beverage data, product images, brewery logos, and profile imagery for a commercial app?
- **Status:** Starting points for review, not legal determinations. Confirm the current license and terms for the exact data, image, API, and intended use before importing or publishing anything.

## Core principle

Online availability does not grant permission to redistribute or display an image in a commercial app. Each source must have a documented, appropriate permission basis. Automate source metadata collection and apply source-specific approval rules; anything without a known, acceptable permission basis is not published.

## Candidate sources

### Manufacturer-provided images (preferred)

Accurate product photography from brewery media kits, official product pages, or direct submissions. Obtain and retain the permission terms; a public website alone is not permission.

### Open Food Facts

Potential source for packaged-beverage data and contributor-submitted images. Before bulk reuse, review: the applicable database and image licenses, attribution and ShareAlike obligations, and any separate rights in depicted logos or packaging.

- https://world.openfoodfacts.org/
- https://openfoodfacts.github.io/documentation/

### Open Brewery DB

Potential supplementary brewery information. Not a comprehensive source of packaged-beverage photography.

- https://www.openbrewerydb.org/

### Original fallback artwork

Create original illustrations for categories (lager, IPA, stout, cider, seltzer, etc.) so the app looks complete when no licensed product image exists. No third-party rights involved.

### User avatars

User-uploaded images with clear terms, or an original selectable avatar library. Do not scrape profile pictures from other platforms.

### Collections and badges

Original commissioned or generated artwork where possible.

## Approaches to avoid

- **Do not scrape Untappd images or data.** Its API terms prohibit using its API to build a competing beer database. (https://untappd.com/api/docs)
- **Do not use Unsplash as a bulk beer-image catalog.** Its API terms and restrictions make it a poor fit. (https://unsplash.com/license)
- **Do not assume** that a dataset described as free, old, or publicly accessible is legally reusable. This applies directly to the legacy catalog (circa 2008 dataset): audit its provenance and reuse rights before reuse or redistribution.

## Provenance metadata (proposed fields per asset)

beverageId, sourceType (manufacturer, Open Food Facts, user upload, original artwork, etc.), sourceUrl, storageKey (only when hosting a copy is permitted), licenseType, attribution, licenseUrl, verifiedAt, status (pending review, approved, rejected, removed).

## Limitations

This research was compiled from the relaunch plan, not from a fresh review of each license. License terms change; re-verify each source at import time and record the verification date in the asset metadata.

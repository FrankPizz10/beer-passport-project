# Image Licensing Assessment

Research date: 2026-10-13. This assessment translates licensing findings
into implementable rules for the image-sourcing experiment. It is not
legal advice. Unresolved questions are listed at the end.

## Authoritative sources checked

- OFF license tutorial (primary): https://openfoodfacts.github.io/documentation/docs/Product-Opener/api/tutorials/license-be-on-the-legal-side/ (accessed 2026-10-13)
- OFF API image fields (primary, verified live 2026-10-13): product
  JSON exposes `image_url`, `image_front_url`, and an `images` dict with
  per-upload `uploader` and size variants.
- OFF wiki attribution guidelines: exists per the tutorial, but the
  wiki is behind a bot check (Anubis) and could not be read. Exact
  attribution format is UNVERIFIED.
- OFF contributor guidance on manufacturer-site pictures: the support
  page returned HTTP 500 on 2026-10-13. OFF's position is UNVERIFIED.

## Verified findings

1. **Three license tiers.** The OFF database is under the Open Database
   License (ODbL); individual database contents under the Database
   Contents License (DbCL); product images under Creative Commons
   Attribution-ShareAlike (CC BY-SA).
2. **OFF's own image caveat.** Product images "may contain graphical
   elements subject to copyright or other rights" (label artwork,
   logos). The CC BY-SA license on the photo does not clear embedded
   third-party rights.
3. **Per-image metadata available.** The API returns the image URL and
   the uploader for each raw upload. There is no per-image license
   version field in the product JSON; the applicable license is the
   project-wide CC BY-SA statement. Do not assert identical terms for
   every image; record what the source states.
4. **Attribution is required** by CC BY-SA. The exact format OFF wants
   (beyond the license's own requirements) is unverified.
5. **ShareAlike applies to adaptations.** Displaying an unmodified image
   next to independent catalog data is not an adaptation of the image.
   Cropping, compositing, or recoloring likely is. Do not modify images
   without review.
6. **Manufacturer images have no implied permission.** An image on a
   brand's website is not authorized for reuse by being visible. Only
   documented permission (license statement, written grant) counts.

## Implementation rules

- R1. Every image candidate records: source URL, image URL, license
  name/version as stated by the source, uploader/contributor when
  available, retrieval date, and the evidence for its reuse basis.
- R2. Unknown or unverifiable rights status is NEVER permission. Such
  candidates are classified `rights_review`, never approved.
- R3. Product-match and rights-review are independent statuses. A
  correct image with bad rights is unusable; a well-licensed image of
  the wrong product is unusable.
- R4. Do not download or retain image binaries during discovery. Store
  URLs and metadata only, until retention is explicitly approved.
- R5. Do not modify images (no cropping/resizing for storage) without
  a ShareAlike review.
- R6. Manufacturer candidates require documented permission covering
  commercial app use and hosting copies, with scope, attribution,
  modification, and expiry terms recorded. Discovery on a manufacturer
  site is not authorization.
- R7. Keep licensed image assets logically separate from catalog data
  in outputs, so attribution and license travel with the image.

## Unresolved questions (need legal review before production)

- Exact OFF attribution format and placement.
- CC BY-SA version applicable to a given image (3.0 vs 4.0).
- Whether displaying OFF images in a commercial app triggers any
  additional obligation beyond BY-SA compliance.
- Embedded trademark/logo risk for label artwork in product photos.
- OFF's position on manufacturer-supplied product pictures.

## Related

- Image readiness checklist: `06-image-readiness-checklist.md`
- Source governance: `03-source-and-data-governance.md`
- Implementation plan: `08-image-sourcing-plan.md`

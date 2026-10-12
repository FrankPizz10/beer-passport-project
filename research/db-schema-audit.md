# BeerPassport Database Schema Audit

- **Date:** October 12, 2026
- **Source:** `FrankPizz10/beer-passport-server`, `prisma/schema.prisma` (7,967 chars, retrieved in full via the GitHub connector at ref `9b19504c`, branch `master`), plus a directory listing of `prisma/migrations/`.
- **Scope:** Read-only. No code, migrations, or data were modified.

## 1. Complete model inventory

**Datasource / generator:** `provider = "mysql"`, `url = env("DATABASE_URL")`, `prisma-client-js`. No enums except `NotificationType`.

### `beers`
```
id               Int                @id @default(autoincrement())
brewery_id       Int?
name             String             @default("") @db.VarChar(255)
cat_id           Int?
style_id         Int?
abv              Float?             @db.Float
ibu              Float?             @db.Float
srm              Float?             @db.Float
upc              Int?
descript         String?            @db.Text
last_mod         DateTime           @default(now()) @db.Timestamp(0)
brewery          breweries?         @relation(fields: [brewery_id], references: [id], onDelete: NoAction, onUpdate: NoAction, map: "fk_beers_brewery_id")
category         categories?        @relation(fields: [cat_id], references: [id], onDelete: NoAction, onUpdate: NoAction, map: "fk_beers_cat_id")
style            styles?            @relation(fields: [style_id], references: [id], onDelete: NoAction, onUpdate: NoAction, map: "fk_beers_style_id")
collection_beers collection_beers[]
user_beers       user_beers[]

@@unique([brewery_id, name])
@@index([brewery_id], map: "fk_beers_brewery_id")
@@index([cat_id], map: "fk_beers_cat_id")
@@index([style_id], map: "fk_beers_style_id")
```
Notes: no image fields of any kind; `upc` is `Int?`; only timestamp is `last_mod`; `descript` is truncated naming.

### `breweries`
```
id       Int      @id @default(autoincrement())
name     String   @default("") @db.VarChar(255)
address1 String   @default("") @db.VarChar(255)
address2 String   @default("") @db.VarChar(255)
city     String   @default("") @db.VarChar(255)
state    String   @default("") @db.VarChar(255)
code     String   @default("") @db.VarChar(25)
country  String   @default("") @db.VarChar(255)
phone    String   @default("") @db.VarChar(50)
website  String   @default("") @db.VarChar(255)
descript String   @db.Text
add_user Int      @default(0)
last_mod DateTime @default(now()) @db.Timestamp(0)
beers    beers[]

@@unique([name], map: "name")
```
Notes: `descript` is required (`String`, no `?`); `add_user` is a magic-number FK with no relation; no city/state index.

### `breweries_geocode`
```
id         Int    @id @default(autoincrement())
brewery_id Int    @default(0)
latitude   Float  @default(0) @db.Float
longitude  Float  @default(0) @db.Float
accuracy   String @default("") @db.VarChar(255)
```
Notes: no relations at all; `brewery_id` is a bare `Int` with no FK, no index; no timestamps. Orphaned/legacy table.

### `categories`
```
id       Int      @id @default(autoincrement())
cat_name String   @default("") @db.VarChar(255)
last_mod DateTime @default(now()) @db.Timestamp(0)
beers    beers[]
styles   styles[]

@@unique([cat_name], map: "cat_name")
```

### `styles`
```
id         Int         @id @default(autoincrement())
cat_id     Int?        @default(11)
style_name String      @default("") @db.VarChar(255)
last_mod   DateTime    @default(now()) @db.Timestamp(0)
category   categories? @relation(fields: [cat_id], references: [id], onDelete: NoAction, onUpdate: NoAction, map: "fk_styles_cat_id")
beers      beers[]

@@unique([style_name], map: "style_name")
@@index([cat_id], map: "fk_styles_cat_id")
```
Notes: `cat_id` defaults to the magic number `11` (a specific category id).

### `user_beers`
```
id         Int       @id @default(autoincrement())
user_id    Int
beer_id    Int
liked      Boolean   @default(false)
created_at DateTime? @default(now()) @db.Timestamp(0)
updated_at DateTime? @default(now()) @db.Timestamp(0)
users      users     @relation(fields: [user_id], references: [id], onDelete: Cascade, onUpdate: NoAction, map: "fk_user_beers_user_id")
beers      beers     @relation(fields: [beer_id], references: [id], onDelete: Cascade, onUpdate: NoAction, map: "fk_user_beers_beer_id")

@@unique([user_id, beer_id])
@@index([beer_id], map: "fk_user_beers_beer_id")
@@index([user_id], map: "fk_user_beers_user_id")
```
Notes: relation field names are plural (`users`, `beers`) for singular relations; only `liked` state exists, no want-to-try.

### `users`
```
id                            Int             @id @unique(map: "id") @default(autoincrement())
uid                           String          @unique(map: "uid") @db.VarChar(255)
notification_token            String?         @unique @db.VarChar(255)
age                           Int
email                         String          @unique(map: "email") @db.VarChar(255)
user_name                     String          @unique(map: "user_name") @db.VarChar(255)
private                       Boolean         @default(false)
friends_friends_user_1Tousers friends[]       @relation("friends_user_1Tousers")
friends_friends_user_2Tousers friends[]       @relation("friends_user_2Tousers")
user_badges                   user_badges[]
user_beers                    user_beers[]
notifications                 notifications[]
```
Notes: redundant `@unique(map: "id")` on the `@id` field; **no `created_at`/`updated_at`**; `age` is a required `Int` with no default.

### `collections`
```
id               Int                @id @default(autoincrement())
name             String             @db.VarChar(255)
difficulty       Int
description      String             @db.VarChar(255)
created_at       DateTime?          @default(now()) @db.Timestamp(0)
updated_at       DateTime?          @default(now()) @db.Timestamp(0)
collection_beers collection_beers[]
user_badges      user_badges[]

@@unique([name], map: "name")
```
Notes: `difficulty` is a free `Int` (no enum/range); `name` has no `@default("")` unlike other name fields (inconsistent).

### `user_badges`
```
id            Int         @id @default(autoincrement())
user_id       Int
collection_id Int
earned        Boolean     @default(false)
progress      Float       @default(0) @db.Float
created_at    DateTime    @default(now()) @db.Timestamp(0)
updated_at    DateTime    @default(now()) @db.Timestamp(0)
users         users       @relation(fields: [user_id], references: [id], onDelete: Cascade, onUpdate: NoAction, map: "fk_user_badges_user_id")
collections   collections @relation(fields: [collection_id], references: [id], onDelete: Cascade, onUpdate: NoAction, map: "fk_user_badges_collection_id")

@@unique([user_id, collection_id], map: "user_id_collection_id")
@@index([collection_id], map: "collection_id")
```
Notes: `@@unique([user_id, collection_id])` supports idempotent upsert; no `earned_at` timestamp; `earned` is a mutable boolean.

### `collection_beers`
```
id            Int         @id @default(autoincrement())
collection_id Int
beer_id       Int
created_at    DateTime?   @default(now()) @db.Timestamp(0)
updated_at    DateTime?   @default(now()) @db.Timestamp(0)
collections   collections @relation(fields: [collection_id], references: [id], onDelete: Cascade, onUpdate: NoAction, map: "fk_collection_id")
beers         beers       @relation(fields: [beer_id], references: [id], onDelete: Cascade, onUpdate: NoAction, map: "fk_beer_id")

@@unique([collection_id, beer_id], map: "collection_id_beer_id")
@@index([beer_id], map: "beer_id")
```

### `friends`
```
id                          Int      @id @default(autoincrement())
user_1                      Int
user_2                      Int
created_at                  DateTime @default(now()) @db.Timestamp(0)
updated_at                  DateTime @default(now()) @db.Timestamp(0)
users_friends_user_1Tousers users    @relation("friends_user_1Tousers", fields: [user_1], references: [id], onDelete: Cascade, onUpdate: NoAction, map: "friends_ibfk_1")
users_friends_user_2Tousers users    @relation("friends_user_2Tousers", fields: [user_2], references: [id], onDelete: Cascade, onUpdate: NoAction, map: "friends_ibfk_2")

@@unique([user_1, user_2], map: "unique_user_combination")
@@index([user_2], map: "user_2")
```
Notes: `user_1` lookups are covered by the leftmost column of the unique constraint; `user_2` has an explicit index. No direction/status field.

### `notifications`
```
id         Int              @id @default(autoincrement())
user_id    Int
type       NotificationType
message    String           @db.VarChar(255)
created_at DateTime         @default(now()) @db.Timestamp(0)
updated_at DateTime         @default(now()) @db.Timestamp(0)
viewed     Boolean          @default(false)
users      users            @relation(fields: [user_id], references: [id], onDelete: Cascade, onUpdate: NoAction, map: "fk_notifications_user_id")

@@unique([user_id, message], map: "unique_user_id_message")
@@index([user_id], map: "fk_notifications_user_id")
```

### `enum NotificationType`
```
NEW_FRIEND
BADGE_EARNED
```

### `api_keys`
```
id       Int      @id @default(autoincrement())
key      String   @default("") @db.VarChar(255)
last_mod DateTime @default(now()) @db.Timestamp(0)
```
Notes: **no unique constraint on `key`**; no name/label, no revocation flag, no created_at, no last-used timestamp.

## 2. Issue findings

### F-1 (High): `friends` allows reversed duplicate pairs
- **Model/field:** `friends`, `@@unique([user_1, user_2], map: "unique_user_combination")`.
- **Evidence:** The unique constraint covers `(user_1, user_2)` only. Nothing prevents a second row `(B, A)` alongside `(A, B)`.
- **Impact:** Duplicate/reversed friendships, double-counted friend feeds, inconsistent unfriend behavior. Whether the app can create this state depends on application logic and existing data (unverified from schema alone).
- **Remediation:** Decide directional vs mutual. If mutual, enforce a canonical ordering (e.g. always store `user_1 < user_2` via a check constraint or application invariant) and backfill/dedupe existing rows; add tests for reverse-direction requests and self-friending.

### F-2 (High): `beers.upc` is `Int?`, losing leading zeros
- **Model/field:** `beers.upc Int?`.
- **Evidence:** `upc Int?` in the schema above.
- **Impact:** Barcodes are identifiers, not quantities. Integer storage drops leading zeros and cannot hold longer formats (e.g. 13+ digit GTINs exceed 32-bit int range).
- **Remediation:** Change to `String?` with normalization (strip spaces/dashes, preserve leading zeros) and a uniqueness rule; inspect existing values and import sources before migrating.

### F-3 (High): `notifications` uniqueness on `(user_id, message)` collapses repeated events
- **Model/field:** `notifications`, `@@unique([user_id, message], map: "unique_user_id_message")`.
- **Evidence:** Schema line above; handlers upserting on this key turn repeated identical events into updates of one row.
- **Impact:** No true event history for repeated events (e.g. earning the same badge twice, repeated friend events). Badge awarding cannot be audited as a history.
- **Remediation:** Decide per notification type which deduplicate vs which record separately; prefer a stable event id or `(user_id, type, reference_id, created_at)` style uniqueness; keep the message as display text only.

### F-4 (High): `api_keys.key` has no unique constraint
- **Model/field:** `api_keys.key String @default("")`.
- **Evidence:** No `@@unique` or `@unique` on `key`; the model has no name, revocation, or usage fields either.
- **Impact:** Duplicate API keys are possible; key rotation/revocation is not modeled; an empty-string default means uninitialized rows share `key = ""`.
- **Remediation:** Add `@unique` on `key`, remove the `@default("")`, add `name`/`label`, `revoked Boolean @default(false)`, `created_at`, and `last_used_at` fields.

### F-5 (High): Cascade deletes destroy user history and achievements
- **Model/field:** `user_badges.collections` (`onDelete: Cascade`); `user_beers.beers` (`onDelete: Cascade`).
- **Evidence:** `collections collections @relation(..., onDelete: Cascade, ...)` in `user_badges`; `beers beers @relation(..., onDelete: Cascade, ...)` in `user_beers`.
- **Impact:** Deleting a collection deletes all `user_badges` rows for it, wiping earned achievements (the 2.0 plan requires "preserve historical achievements"). Deleting a catalog beer deletes every user's log of that beer. These are the two most destructive cascades in the schema.
- **Remediation:** Change to `NoAction`/`Restrict` for `user_badges → collections` and `user_beers → beers`, or implement soft-delete on `collections`/`beers`. Keep `Cascade` on user deletion (account deletion should remove personal data).

### F-6 (High): No want-to-try state; 2.0 product requirement unmet
- **Model/field:** `user_beers` (`liked Boolean @default(false)` only).
- **Evidence:** The only state beyond row existence is `liked`. The 2.0 plan requires distinguishing tried vs liked vs want-to-try as distinct intentions.
- **Impact:** Cannot implement the planned product detail without a schema change.
- **Remediation:** Add a status representation, e.g. `status` enum (`TRIED`, `LIKED`, `WANT_TO_TRY`) or a separate `want_to_try` flag/table; migrate existing `liked=true` rows accordingly.

### F-7 (High): No image/asset provenance model; 2.0 requirement unmet
- **Model/field:** (absent): `beers` has no image fields at all.
- **Evidence:** Full schema above contains no image, asset, license, or attribution fields on any model.
- **Impact:** The 2.0 plan's image strategy (approved product image → original category illustration → text fallback, with per-asset source/license/attribution/verification metadata) has no schema home.
- **Remediation:** Add a `beverage_images`/`assets` model with the planned fields: `beverage_id`, `source_type`, `source_url`, `storage_key`, `license_type`, `attribution`, `license_url`, `verified_at`, `status` (pending/approved/rejected/removed).

### F-8 (Medium): `breweries_geocode` is an orphaned legacy table
- **Model/field:** `breweries_geocode` (whole model).
- **Evidence:** `brewery_id Int @default(0)` with no `@relation`, no index, no timestamps; nothing references it.
- **Impact:** Dead weight; `brewery_id = 0` rows are meaningless; confusion for future agents.
- **Remediation:** If geocoding is wanted, add a real FK to `breweries` with an index; otherwise drop the table in a migration.

### F-9 (Medium): Magic numbers in schema
- **Model/field:** `styles.cat_id Int? @default(11)`; `breweries.add_user Int @default(0)`.
- **Evidence:** Schema lines above.
- **Impact:** `default(11)` hardcodes a specific category row id; breaks if categories are reseeded with different ids. `add_user = 0` conflates "unknown" with a user id.
- **Remediation:** Remove the `11` default (make it nullable without default or point at a seeded "Uncategorized" row by a stable key); make `add_user Int?` nullable with a real optional relation to `users`.

### F-10 (Medium): `beers @@unique([brewery_id, name])` does not dedupe brewery-less beers
- **Model/field:** `beers`, `@@unique([brewery_id, name])` with `brewery_id Int?`.
- **Evidence:** In MySQL, `NULL != NULL` for unique constraints, so any number of `(NULL, "Same Name")` rows can coexist.
- **Impact:** Duplicate catalog entries for beers with no brewery, undermining the planned duplicate-detection import workflow.
- **Remediation:** Normalize on import (require brewery resolution or use a sentinel), and/or add a generated normalized-name column with a unique index.

### F-11 (Medium): `users` has no audit timestamps; inconsistent timestamp conventions
- **Model/field:** `users` (no `created_at`/`updated_at`); elsewhere `DateTime?` vs `DateTime` varies (`user_beers` nullable, `user_badges` non-null, `friends` non-null).
- **Evidence:** Schema above.
- **Impact:** Cannot answer "when did this user sign up" (needed for activation/retention metrics, a 2.0 success measure); inconsistent nullability complicates queries.
- **Remediation:** Add `created_at`/`updated_at` to `users`; standardize on non-nullable `DateTime @default(now())`.

### F-12 (Medium): `users.notification_token` is `@unique`, limiting users to one device
- **Model/field:** `users.notification_token String? @unique`.
- **Evidence:** Schema line above.
- **Impact:** A user with two devices can only have one push token stored; the second login overwrites or conflicts.
- **Remediation:** Move tokens to a separate `push_tokens` model (user_id, token unique, device info, created_at).

### F-13 (Medium): `users.id` has redundant `@unique` on top of `@id`
- **Model/field:** `users.id Int @id @unique(map: "id")`.
- **Evidence:** Schema line above.
- **Impact:** Creates a redundant unique index alongside the primary key; harmless but sloppy, and the explicit `map: "id"` suggests manual editing.
- **Remediation:** Remove `@unique(map: "id")`.

### F-14 (Medium): `collections.difficulty` is a free `Int`
- **Model/field:** `collections.difficulty Int`.
- **Evidence:** Schema line above.
- **Impact:** No constrained set of difficulty levels; inconsistent data entry.
- **Remediation:** Constrain via enum (`EASY`, `MEDIUM`, `HARD`, …) or a documented 1–5 range with validation.

### F-15 (Low): Truncated/inconsistent naming
- **Model/field:** `beers.descript`, `breweries.descript`; relation fields `users`/`beers` (plural) on `user_beers`; `users_friends_user_1Tousers`.
- **Evidence:** Schema above.
- **Impact:** Readability only; renaming is a breaking Prisma client change, so batch with other breaking changes.
- **Remediation:** Rename to `description` and singular relation names during a planned breaking-change migration.

### F-16 (Low): `notifications` lacks a composite index for feed queries
- **Model/field:** `notifications` indexes.
- **Evidence:** Only `@@index([user_id])` beyond the unique constraint.
- **Impact:** "Unread notifications for user, newest first" queries would benefit from `(user_id, viewed, created_at)`.
- **Remediation:** Add `@@index([user_id, viewed, created_at])` when building the notification feed.

### Positive notes (schema strengths)
- `user_badges @@unique([user_id, collection_id])` makes idempotent badge awarding via upsert straightforward (supports the 2.0 idempotency requirement).
- `collections` + `collection_beers` are already data-driven (supports the 2.0 "definitions data-driven, not hardcoded" requirement).
- `NotificationType` enum exists for the two notification kinds; extend it rather than adding free-text types.
- Foreign-key indexes exist on all FK columns (`beers`, `styles`, `user_beers`, `user_badges`, `collection_beers`, `friends`, `notifications`).
- `users.private Boolean @default(false)` exists for the privacy rules work.

## 3. Migration hygiene

- **15 migrations** in `prisma/migrations/`, from `20230510040312_` through `20240320220324_unique_constraints`, plus `migration_lock.toml`. Names suggest an organic history: `unique_user_beers`, `notifications`, `notification_type`, `unique_notifications`, `api_keys`, `style_cat_fk`, `unique_constraints`.
- The migration names align with the current schema's unique constraints (user_beers, notifications, api_keys all have matching "unique_*" migrations), which suggests the schema and migration history are roughly in sync.
- **Drift not assessed:** confirming schema-vs-database drift requires a live database; none exists (the production MySQL ran on EFS and the service is shut down). Do not claim drift in either direction.

## 4. Prioritized remediation list

**P0: before data migration or production cutover**
- F-5: change destructive cascades (`user_badges` on collection delete, `user_beers` on beer delete) to restrict/no-action or soft-delete.
- F-4: unique constraint on `api_keys.key`, remove empty-string default, add revocation fields.
- F-1: decide friendship directionality; enforce canonical pair ordering.

**P1: before public relaunch**
- F-6: add want-to-try state to the tasting model.
- F-7: add the image/asset provenance model.
- F-2: migrate `upc` to string with normalization.
- F-3: redesign notification uniqueness per event type.
- F-11: add `created_at`/`updated_at` to `users`; standardize timestamp nullability.
- F-10: close the nullable-brewery duplicate loophole (import normalization + unique normalized name).

**P2: during relaunch build**
- F-8: resolve `breweries_geocode` (real FK or drop).
- F-9: remove magic-number defaults (`styles.cat_id = 11`, `add_user = 0`).
- F-12: multi-device push tokens model.
- F-13, F-14, F-15, F-16: cleanup items (redundant unique, difficulty enum, naming, feed index).

## 5. Verified vs inferred

- **Verified:** every model, field, type, constraint, index, relation, and delete behavior quoted in section 1 was read directly from the full `prisma/schema.prisma` file retrieved via the GitHub connector (7,967 chars, ref `9b19504c`). The migration count (15) and names come from a live directory listing of `prisma/migrations/`.
- **Inferred (marked as such):** whether reversed friend pairs or duplicate API keys exist in actual data (requires the database); whether the application logic already guards the flagged cases; schema-vs-database drift (no live database to compare against).
- **Not retrieved:** nothing. The complete schema file was obtained; no section was reconstructed from fragments.

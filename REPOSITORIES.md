# Repositories

Inventory of the five existing BeerPassport repositories, verified against their current state on GitHub in October 2026. All five are owned by `FrankPizz10` and are currently **public**. Last commits range from April 2024 to November 2024; none have been touched in roughly two years.

## 1. beer-passport: React Native/Expo mobile app

- **URL:** https://github.com/FrankPizz10/beer-passport
- **Purpose:** The end-user mobile app: beverage discovery and logging, passport/collections/badges, friends and feed, profiles.
- **Default branch:** `main` | **Visibility:** public | **Last commit:** 2024-11-24 ("release/09-30-24")
- **Technologies (verified from `package.json`):** Expo `^51.0.31`, React Native `0.74.5`, React `18.2.0`, TypeScript `^5.3.0`, React Navigation (bottom-tabs `^6.5.8`, native-stack `^6.9.12`), Firebase client `^9.20.0`, expo-notifications `~0.28.16`, expo-linking `~6.3.1`, expo-updates `~0.25.24`, react-native-dotenv `^3.4.8`.
- **Entry points:** `App.tsx` (AuthProvider > NavigationContainer with `linking` config > DeepLinkProvider > native-stack navigator; initial route `Login`); `props.tsx` (typed navigation params); `Controllers/` (Auth, DeepLink, search, badges); `Models/Requests.ts` (all API calls via `fetch` with the Firebase ID token); `screens/` (20 screens); `app.json` (Expo config: slug `beerpassport`, scheme `beerpassport`, version `1.0.12`, associated domain `applinks:web.beer-passport.com`).
- **Dependencies on other repos:** Calls the Express API at `${EXPO_PUBLIC_API_URL}/api/...` (env-driven, no hardcoded URL). Shares Firebase project `beerpassport-b31d8` with the server, admin, and cloud functions. Universal Links served by `beer-passport-web` for path `/beers/*`.
- **Commands (verified from `package.json`):** `npm start` (`npx tsc && npx expo start`), `expo run:android` / `expo run:ios`, `npm run lint` (`eslint --fix .`). No test script.
- **Documentation gaps:** README is 84 bytes (title plus one emulator command); no setup instructions; no env-var inventory (`EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_API_KEY`, `EXPO_PUBLIC_*` Firebase config, `EXPO_PUBLIC_ENV` are required but undocumented).

## 2. beer-passport-server: Node/Express/TypeScript API

- **URL:** https://github.com/FrankPizz10/beer-passport-server
- **Purpose:** The backend API: authentication/authorization, beverage catalog, user logs, friendships, collections, badges, notifications, push notifications, admin endpoints.
- **Default branch:** `master` | **Visibility:** public | **Last commit:** 2024-08-27 ("release/08-21-24")
- **Technologies (verified from `package.json`):** Express `^4.18.2`, TypeScript `^5.0.4`, `@prisma/client 4.14.0` with Prisma CLI `4.11.0` (version mismatch, confirmed), `mysql2 ^3.6.2`, `@aws-sdk/client-secrets-manager ^3.432.0`, `firebase-admin ^11.10.1`, `expo-server-sdk ^3.7.0`, `@sentry/node ^7.79.0`, `csv-parser ^3.0.0`, Jest `^29.5.0` / ts-jest.
- **Entry points:** `src/index.ts` (Express bootstrap; calls `seedDatabase()` unawaited at startup); `src/Routes/` (`admins.ts`, `beers.ts`, `breweries.ts`, `collectionbeers.ts`, `collections.ts`, `friends.ts`, `notifications.ts`, `userbadges.ts`, `userbeers.ts`, `users.ts`, `secure.ts` for API-key-gated bulk endpoints); `src/Middleware/authUsers.ts` (`decodeUserToken` on `/api`, `decodeAdminToken` on `/admin`, `decodeAPIKey` on `/secure`); `src/DBclient/` (Prisma clients, `seedDatabase.ts`); `src/Environment/environmentVariablesClient.ts` (AWS Secrets Manager to local `.env`); `prisma/schema.prisma` (MySQL provider); `Dockerfile` (`node:lts-alpine`, `EXPOSE 3000`, `CMD ["npm", "run", "start:prod"]`); `data/` (CSV seed data: `beers.csv` 4.1 MB, `breweries.csv`, `categories.csv`, `styles.csv`).
- **Dependencies on other repos:** Verifies Firebase ID tokens against project `beerpassport-b31d8` and the `admin` custom claim set by the cloud function; sends push notifications to the mobile app via the Expo server SDK; dev seeding pulls production catalog data through its own `/secure/api/*` endpoints.
- **Commands (verified from `package.json`):** `npm run build:prod` (`npx tsc` + Sentry sourcemaps), `npm run start:prod` (Secrets Manager fetch, healthcheck, `prisma migrate deploy`, start), `npm run dev` (tsc watch + nodemon), `npm test` (jest), `npm run lint`. CI (`.github/workflows/ci.yml`) runs lint only; build and test steps are commented out.
- **Documentation gaps:** README is 60 bytes; no env-var inventory (`PORT`, `DATABASE_URL`, `MYSQL_*`, `SECRET_NAME`, `PROD_API_URL`, `PROD_API_KEY`, `ENVIRONMENT`, `FIREBASE_*` service-account fields, `SENTRY_DSN`); no API documentation (routes, auth requirements, and shapes exist only in code); one test file total (`test/DBClient/gettableinfo.test.ts`); API hosting target undocumented.

## 3. beer-passport-admin: React (CRA) admin dashboard

- **URL:** https://github.com/FrankPizz10/beer-passport-admin
- **Purpose:** Internal admin site: catalog CRUD (beers, breweries, categories, styles, collections, collection-beer links), API key generation, admin-role assignment, analytics.
- **Default branch:** `master` | **Visibility:** public | **Last commit:** 2024-04-17 ("analytics")
- **Technologies (verified from `package.json`):** React `^18.2.0`, react-scripts `5.0.1` (Create React App), TypeScript `^4.9.5`, react-router-dom `^6.14.2`, Firebase `^10.1.0`, react-chartjs-2, react-countup.
- **Entry points:** `src/index.tsx` to `src/App.tsx` (routes: `/` = `SignInPage`, `/admin` = `AdminHomePage`); `src/MainScreen/` (`AdminHomePage` with DatabaseMod / AdminTasks / Analytics tabs, `SignInPage` gated on the `admin` custom claim, `MakeAdminForm`, `AdminTasks`, `Analytics` + `ChartComponents/`); entity forms (`BeerForm`, `BreweryForm`, `CategoryForm`, `StyleForm`, `CollectionForm`, `CollectionBeerForm`).
- **Dependencies on other repos:** Talks to the Express API at `${REACT_APP_API_URL}` (env-driven); uses `/admin/*` and `/secure/api/*` endpoints; same Firebase Auth project; `MakeAdminForm` calls the `addAdminRole` callable cloud function. Deploys to S3 bucket `beerpassportadmin` + CloudFront (per the `deploy` script).
- **Commands (verified from `package.json`):** standard CRA `start`/`build`/`test`; `npm run deploy` (`npm run build && aws s3 sync ./build s3://beerpassportadmin --delete && aws cloudfront create-invalidation ...`).
- **Documentation gaps:** README is 44 bytes; no setup instructions; no env-var inventory (`REACT_APP_API_URL`, `REACT_APP_*` Firebase vars).

## 4. beer-passport-web: Vite marketing/link site

- **URL:** https://github.com/FrankPizz10/beer-passport-web
- **Purpose:** Public landing page ("BeerPassport / Pour Your Path.") with app-store links, and the host for the Apple App Site Association file used by Universal Links.
- **Default branch:** `main` | **Visibility:** public | **Last commit:** 2024-10-01 ("Adjusted mobile styling")
- **Technologies (verified from `package.json`):** React `^18.3.1`, Vite `^5.4.1`, react-router-dom `^6.26.2`, TypeScript `^5.5.3`, framer-motion, react-icons.
- **Entry points:** `src/main.tsx` to `src/App.tsx` (routes: `/` = `Home`, `/beers/*` = `Home`, `/apple-app-site-association` and `/.well-known/apple-app-site-association` = `Rewriter`); `src/pages/home.tsx` (landing page with QR code, App Store link, Android APK download); `src/pages/rewritter.tsx` (renders the association JSON inside a `<pre>` element, which breaks Universal Link validation); `src/assets/apple-app-site-association.json` (appID `29QUQCCQ87.com.beerpassport`, paths `/beers/*`).
- **Dependencies on other repos:** Serves the iOS universal-link file for the mobile app's `applinks:web.beer-passport.com` domain.
- **Commands (verified from `package.json`):** `npm run dev` (vite), `npm run build` (`tsc -b && vite build`), `npm run lint`, `npm run preview`.
- **Documentation gaps:** README is stock Vite boilerplate and says nothing about BeerPassport; web hosting target undocumented.

## 5. beerpassport-cloud-functions: Firebase Cloud Functions

- **URL:** https://github.com/FrankPizz10/beerpassport-cloud-functions
- **Purpose:** Firebase Auth custom-claim management (admin roles). No README.
- **Default branch:** `master` | **Visibility:** public | **Last commit:** 2023-07-29 ("Secured and Fixed addAdminRole")
- **Technologies (verified from `functions/package.json`):** `firebase-functions ^4.3.1` (v2 API), `firebase-admin ^11.8.0`, Node 18 engine.
- **Entry points:** `functions/index.js` (1,412 bytes) defines two functions: `helloWorld` (`onRequest`, returns "Hello from Firebase!", unused scaffolding) and `addAdminRole` (`onCall` callable; requires `request.auth.token.admin === true`, then sets the `admin` custom claim for a given email). Also `firebase.json`, `firestore.rules`, `.firebaserc` (project `beerpassport-b31d8`).
- **Dependencies on other repos:** Called only by the admin dashboard's `MakeAdminForm`. The server verifies the claims this function sets.
- **Commands (verified from `package.json`):** `npm run deploy` (`firebase deploy --only functions`), `npm run serve` (emulators), `npm run logs`.
- **Documentation gaps:** No README at all. **Security note (observed in code, not a verified exploit):** `firestore.rules` allows open read/write on `/users/{userId}` for any caller. This was not in the original audit; it needs verification against the deployed rules and a fix before any relaunch.

## Canonical ownership (verified)

- Mobile UX and deep-link handling: `beer-passport`.
- API, data model, auth enforcement, notifications: `beer-passport-server`.
- Catalog administration and admin tooling: `beer-passport-admin`.
- Public web presence and Universal Link association file: `beer-passport-web`.
- Admin custom-claim assignment: `beerpassport-cloud-functions`.
- Shared identity: Firebase project `beerpassport-b31d8` (Auth used by mobile, server, admin, and cloud functions).

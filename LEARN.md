# LEARN

One short section per milestone: what was built, a map of the key files,
the new ideas, and the commands. Read it after each milestone, then do
that milestone's exercise in `exercises/`.

---

## M1 · Skeleton

**What we built.** A monorepo with an API that answers `/health` and checks its
database, a PostgreSQL database in Docker, and an Expo app with five tabs, a
floating "island" tab bar, dark/light themes and three languages. Nothing
handles money yet. M1 is the frame the next eight milestones fill in.

**Files**

| File | What it does |
|---|---|
| `docker-compose.yml` | Starts PostgreSQL and the API together, with one command. |
| `api/app/main.py` | Builds the FastAPI app: CORS settings, then the routers under `/api/v1`. |
| `api/app/config.py` | Reads settings (database URL, allowed origins) from env vars, with types checked at startup. |
| `api/app/db.py` | One connection pool per process; hands each request a database session. |
| `api/app/routers/health.py` | `GET /api/v1/health`: 200 if a real `SELECT 1` works, 503 if the database is down. |
| `api/alembic/versions/0001_baseline.py` | Empty first migration, so M2's tables have a parent revision. |
| `api/tests/` | pytest tests against a real Postgres (`sewe_test`): health, CORS, migrations. |
| `app/app/_layout.tsx` | Root of every screen: loads fonts, starts i18n, provides the theme. |
| `app/app/(tabs)/_layout.tsx` | Declares the 5 tabs and swaps the default tab bar for the island. |
| `app/app/(tabs)/*.tsx` | One file per tab. Accounts shows the empty state; the others are placeholders. |
| `app/theme/tokens.ts` | Every color, size and radius for both themes, from the design canvas. |
| `app/theme/resolveTheme.ts` | Turns "system/dark/light" + the device setting into the theme to draw. |
| `app/theme/ThemeProvider.tsx` | React context that holds the theme choice, saves it, and gives colors to components. |
| `app/i18n/*.json`, `index.ts` | All visible text in EN/FR/ES; picks the saved or device language. |
| `app/components/IslandNav.tsx` | Draws the floating tab bar; the router does the actual navigation. |
| `app/tests/` | Jest tests: translation-key parity, theme switching, real navigation. |
| `.github/workflows/ci.yml` | Runs lint, types and tests for API and app on every push. |

**New concepts**

- **Dependency injection (FastAPI `Depends`):** a route *asks* for a database session instead of creating one, so a test can swap in a fake (`test_health_503_when_database_down` does exactly that).
- **React context:** a value (the theme) that any component below the provider can read with a hook (`useTheme()`), with no props passed down by hand.
- **File-based routing (Expo Router):** the file `app/(tabs)/reports.tsx` *is* the `/reports` page. The `(tabs)` folder groups routes without adding to the URL.

**Commands**

| Command | What it does |
|---|---|
| `docker compose up --build` | Builds the API image and starts Postgres + API; `--build` picks up code changes. |
| `uv run pytest` | Runs the API tests inside the project's virtual environment (`uv` manages it). |
| `uv run alembic upgrade head` | Applies every migration the database doesn't have yet. |
| `npm run web` | Starts the Expo dev server and opens the web app on port 8081. |
| `npm test` / `npm run lint` / `npm run typecheck` | App tests, lint rules, and TypeScript type checking. |

**Try it.** Add a fourth language. Create `i18n/de.json` with only
`{"tabs": {"accounts": "Konten"}}`, add `'de'` to `LANGUAGES` and `resources`
in `i18n/index.ts`, and run `npm test`. The parity test fails and lists
every missing key; fill them in until it passes.

---

## M2 · Auth and security

**What we built.** Accounts: sign up with an emailed code, sign in with a
password plus an authenticator-app code (or a passkey on the web), stay
signed in with a rotating refresh token, and sign out everywhere it
matters. The API refuses requests from other websites (the Origin check),
counts attempts (rate limits), and never stores a secret in plain text.

**Files**

| File | What it does |
|---|---|
| `api/app/routers/auth.py` | Signup, verify-email, login, refresh, logout. |
| `api/app/routers/two_factor.py` | TOTP setup and verify, recovery codes. |
| `api/app/routers/passkeys.py` | Web passkey register and sign-in (py_webauthn). |
| `api/app/routers/sessions.py`, `settings.py`, `me.py` | Active sessions + revoke; theme/language; "who am I". |
| `api/app/security/sessions.py` | Starts sessions; refresh rotation, 20 s grace, reuse detection. |
| `api/app/security/tokens.py` | JWTs with a pinned algorithm and a `purpose`; refresh token format. |
| `api/app/security/totp.py` | RFC 6238 one-time codes, standard library only (your exercise). |
| `api/app/security/hashing.py`, `encryption.py` | Keyed hashes + constant-time compare; AES-GCM for the TOTP secret. |
| `api/app/security/origin.py`, `cookies.py`, `rate_limit.py` | The Origin check, the one cookie, attempt limits. |
| `api/app/security/deps.py` | `get_current_auth`: checks the token **and** that its session is still live. |
| `api/app/services/email.py` | Console sender (local) or Resend (prod), one interface. |
| `app/lib/api.ts`, `tokens.ts` | Typed API client with one shared refresh; where tokens live. |
| `app/auth/AuthProvider.tsx` | Sign-in state for the whole app; syncs theme/language. |
| `app/app/(auth)/`, `(onboarding)/` | Sign-in screens; TOTP setup and the passkey offer. |

**New concepts**

- **Refresh-token rotation:** each refresh swaps the token for a new one, so a stolen old token is worth nothing, and if it shows up again we know it was stolen and end the session (`rotate_refresh_token`).
- **TOTP:** your phone and the server share a secret; every 30 s both compute HMAC(secret, time ÷ 30) and keep 6 digits. Matching digits prove you hold the secret without ever sending it (`security/totp.py`).
- **Conditional UPDATE:** `UPDATE … WHERE last_step < :step` lets the database, not Python, decide which of two simultaneous requests wins (`_consume_totp_code`).

**Commands**

| Command | What it does |
|---|---|
| `docker compose logs api` | Shows the API log, where the console sender prints verification codes. |
| `uv run pytest --cov=app/security --cov=app/services` | Tests plus coverage of the security code (CI needs ≥ 80%). |
| `uv run alembic revision --autogenerate -m "..."` | Writes a migration from the model changes; always read it before committing. |
| `uv run pytest ../exercises/M2` | Runs your `verify_totp` against the exercise tests. |

**Try it.** In `api/app/config.py`, change `refresh_grace_seconds` to `0`
and run `uv run pytest tests/test_refresh.py`. The grace test fails: a
second tab refreshing a moment later would now log you out. Put it back.

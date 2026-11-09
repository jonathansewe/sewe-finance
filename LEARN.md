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

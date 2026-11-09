# SEWE Finance V1 · Build Spec for Claude Code

Version 1.2 · 2026-11-06 · Owner: Jonathan Sewe

> **What changed in v1.2.** v1.2 applies Jonathan's answers to the v1.1 open
> questions, cuts V1 down to ship faster (the cut items move to section 13,
> "V1.1"), adds six security fixes, re-estimates the timeline, and shortens
> the teaching deliverables. Decisions D-15 to D-30 are new; see
> `docs/DECISIONS.md`. Tags like `[D-16]` mark where each one landed.
>
> | Change | Decision |
> |---|---|
> | Domain layout under `jonathansewe.com`; passkeys scoped to `finance.jonathansewe.com` | D-15 |
> | Origin check on `/auth/refresh` and every POST/PATCH/DELETE | D-16 |
> | Cookies never carry a `Domain` attribute (tested) | D-17 |
> | Logout revokes by the session ID inside the access token | D-18 |
> | Each account is locked to its first import format | D-19 |
> | Backup heartbeat alert after 48 h without a backup | D-20 |
> | D-07 corrected: which models reject forced `tool_choice`, with sources | D-21 |
> | V1 cuts moved to V1.1 (native passkeys, EAS, app stores, voice, PDF import, gamification, device cap) | D-22 |
> | Re-estimate: ≈ 118 h ≈ 6 weeks | D-23 |
> | Teaching trimmed to a short LEARN.md section and one exercise per milestone | D-24 |
> | Email via Resend behind `services/email.py` | D-25 |
> | P1 rules reworded honestly; legacy data is invented | D-26 |
> | Masking covers PayPal, Apple Cash, "TRANSFER TO/FROM <name>" | D-27 |
> | Design canvas linked; this spec wins where they differ | D-28 |
> | Hosting stays non-commercial; live-model eval approved | D-29 |
> | Branch workflow and push rights | D-30 |

---

## 1. How to use this spec

Build SEWE Finance V1 milestone by milestone (section 10), stopping after
each one for review. The owner, Jonathan Sewe, must be able to explain and
rewrite every line, so readable code beats clever code. The goal is to
**ship as fast as possible** while keeping the short per-milestone teaching.

**Working rules for Claude Code**

1. Read this whole spec before writing code.
2. Work on one milestone at a time. Do not start the next until all its acceptance criteria pass.
3. Write tests with the feature, not after. Run the full test suite before every commit.
4. One commit per logical change, using Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`, `ci:`).
5. Work on a branch and open a pull request; never push to `main` directly. `[D-30]`
6. Never commit secrets. Every secret lives in `.env`; ship `.env.example` with placeholder values.
7. Prefer the standard library and well-known packages. Add a dependency only when it saves real work, and note why in the commit message.
8. Comment the WHY, not the WHAT. Every module starts with a 3 to 5 line header comment explaining its job.
9. When the spec is ambiguous, choose the simplest option, write it in `docs/DECISIONS.md` (date, decision, reason, rejected alternative), and continue.
10. At the end of each milestone, add its `LEARN.md` section and its rewrite exercise (section 12). `[D-24]`

**Definition of done for V1**

- Jonathan can sign up, import a real bank statement (CSV or OFX/QFX), and see categorized transactions, reports, and AI chat answers based on his own data.
- Works in a desktop browser and a phone browser at `https://finance.jonathansewe.com`. `[D-15]`
- English, French and Spanish; dark and light themes.
- All tests pass in CI; web and API are deployed; backups run and alert when they stop; the README has screenshots and setup steps.

---

## 2. Product and V1 scope

SEWE Finance is a personal-finance app that reads your money, sorts it with
AI, and answers questions about it. V1 is read-only: it never moves money.

**Primary user:** an individual managing several bank accounts, who sends
money to family, pays cash for some purchases, and wants to understand where
money goes. The first real user is Jonathan himself.

| In V1 | Out of V1 |
|---|---|
| Sign up, email verification, web passkey login, TOTP two-factor + recovery codes, active-sessions list with revoke `[D-22]` | Money transfers between accounts or banks |
| Bank statement import: CSV, OFX, QFX | Live bank connection (Plaid or similar) |
| AI categorization + user-defined categories (for example "Mom") that learn from corrections | Investment accounts and investment suggestions |
| Reports: day, week, month, year, custom range; by category; subscriptions; trends | Credit score tracking (never store SSNs) |
| Receipt scan with AI extraction, user review, cash expenses | Insurance tracking, tax reports |
| AI chat over the user's own data (text) | Courses, quizzes, psychology assessment |
| Settings: theme (dark/light/system), language (EN/FR/ES), data export, AI provider | Fully local on-device AI model |
| Web deploy | **Moved to V1.1 (section 13):** native passkeys, EAS builds, app stores, voice input, PDF import, gamification, 3-device cap `[D-22]` |

The Expo app still runs on iOS and Android during development (Expo Go), but
V1 ships to the web only.

The chat gives educational information only and must say so. It never
presents itself as a licensed financial advisor.

---

## 3. Tech stack

Decision: an Expo (React Native) app in TypeScript, talking to a FastAPI
backend in Python, with PostgreSQL. One frontend codebase can reach web, iOS
and Android, and the AI work stays in Python.

```
                                        ┌─────────────────────────────┐
                                        │ PostgreSQL (Neon)  [D-03]   │
┌───────────────────────────┐           └─────────────────────────────┘
│ Expo web app              │ HTTPS     ┌─────────────────────────────┐
│ finance.jonathansewe.com  │──────────▶│ FastAPI                     │──▶ Cloudflare R2 (receipts, backups)
│ (Vercel)                  │ + Origin  │ api.finance.jonathansewe.com│──▶ Claude API (masked, minimal)
└───────────────────────────┘  check    │ (Render)                    │──▶ Resend (email codes)  [D-25]
                                        └─────────────────────────────┘
  jonathansewe.com = resume site (Netlify, separate repo, same site for cookies) [D-15]
```

The app only ever calls the API. Secrets, the database, object storage, the
email key and the AI key never reach the browser.

| Option | Strength | Why not chosen |
|---|---|---|
| **Expo + FastAPI + PostgreSQL (chosen)** | One UI codebase for web and later both stores; Python for AI and data parsing; grows out of the P1 Python project | Two languages to learn, which is the point |
| Next.js full stack + PostgreSQL | Fastest web launch, one language | App stores later need a second app or a wrapper Apple may reject |
| Streamlit (Python only) | Fastest to build | Not a real mobile app; looks like a prototype on a resume |
| Firebase or Supabase only | Little backend code | Hides the backend skills this project exists to show |

**Frontend:** Expo SDK (latest stable), Expo Router, TypeScript strict mode,
`i18next` + `react-i18next`, `react-native-svg` for icons and charts,
`expo-camera` and `expo-image-picker` for receipts, `expo-document-picker`
for statements, `expo-secure-store` for tokens on device.

**Backend:** Python 3.12, FastAPI, SQLAlchemy 2 + Alembic migrations,
Pydantic v2, `pytest`, `argon2-cffi`, `pyotp`, `webauthn` (py_webauthn),
`ofxparse`, `google-re2`, `boto3` (R2), `resend` (email, behind
`services/email.py`) `[D-25]`, the official `anthropic` SDK.

**AI models:** set through env vars, never hard-coded.
`AI_MODEL_FAST=claude-haiku-5-5` for categorization;
`AI_MODEL_SMART=claude-sonnet-5-5` for chat and receipt vision. Wrap all AI
calls behind one `ai/provider.py` interface so another provider
(bring-your-own-key) can be added later.

**Hosting** `[D-15]`:

| Piece | Where | Address |
|---|---|---|
| Resume site (not this repo) | Netlify | `https://jonathansewe.com` |
| SEWE Finance web (static Expo web export) | Vercel (Hobby; non-commercial, see D-29) | `https://finance.jonathansewe.com` |
| SEWE Finance API | Render web service | `https://api.finance.jonathansewe.com` |
| Database | Neon Postgres | private connection string |
| Receipt images and backups | Cloudflare R2, private buckets | signed URLs only |
| DNS | Cloudflare (`jonathansewe.com` zone) | CNAMEs for `finance` and `api.finance` |
| Email | Resend, sending from `jonathansewe.com` (shared across projects) | — |

**Repo:** `github.com/jonathansewe/sewe-finance` (renamed from
`expense-categorizer`; GitHub redirects the old name).

---

## 4. Repository layout

One monorepo with two apps. The old P1 script lives in `legacy/` so its
history stays visible.

```
sewe-finance/
  README.md            # pitch, screenshots, setup, architecture
  LEARN.md             # one short section per milestone [D-24]
  .env.example
  docker-compose.yml   # local Postgres + API
  .github/workflows/
    ci.yml             # lint + tests on every push and PR
    backup.yml         # nightly pg_dump → R2 + heartbeat ping (M9) [D-20]
  docs/
    SPEC.md            # this document
    DECISIONS.md       # every judgment call, dated
    OPEN_QUESTIONS.md  # questions waiting on the owner
  exercises/
    M1/ ... M9/        # rewrite-yourself exercises: README + tests [D-24]
  legacy/              # original P1 script + its invented sample data [D-26]
  api/                 # FastAPI backend
    app/
      main.py          # app factory, routers, CORS, Origin check
      config.py        # settings from env vars
      db.py            # engine, session
      models/          # SQLAlchemy tables (section 5)
      schemas/         # Pydantic request/response models
      routers/         # auth, sessions, accounts, imports, transactions,
                       # categories, reports, receipts, chat, settings
      services/
        parsers/       # csv_parser.py, ofx_parser.py
        dedupe.py      # FITID / occurrence-index keys [D-01]
        categorizer.py # rules first, then AI
        masking.py     # person-name masking before any AI call [D-09][D-27]
        subscriptions.py
        reports.py     # the only place totals are computed [D-07]
        storage.py     # R2 upload, signed URLs, delete [D-04]
        email.py       # EmailSender interface; Resend + console senders [D-25]
      ai/
        provider.py    # interface
        anthropic_provider.py
        chat_tools.py  # tool definitions that wrap reports.py [D-07]
        prompts/       # one file per prompt, versioned
      security/        # passwords, totp, webauthn, tokens, encryption, origin
    alembic/
    tests/
  app/                 # Expo app
    app/               # Expo Router screens: (tabs)/accounts, reports,
                       # receipt, chat, settings; later (auth)/ and import.tsx
    components/        # Island nav, Header, Card, Segmented, TxRow, Bar chart
    theme/             # tokens.ts (dark + light), ThemeProvider, resolveTheme
    i18n/              # en.json, fr.json, es.json, index.ts
    lib/api.ts         # typed API client
    tests/
```

---

## 5. Data model

Amounts are stored as integer cents (`amount_cents`), never floats; negative
= money out. Every table has `id` (UUID), `created_at`, `updated_at`, and
every user-owned row has `user_id`, checked on every query.

| Table | Key columns | Notes |
|---|---|---|
| users | email (unique), password_hash, email_verified_at, totp_secret_enc, display_name | `totp_secret_enc` encrypted at rest |
| user_settings | user_id, theme (`dark` / `light` / `system`), language (`en` / `fr` / `es`), currency (`USD`), ai_provider, monthly_budget_cents | One row per user |
| sessions | user_id, refresh_token_hash, user_agent_summary, last_seen_at, expires_at, revoked_at | One row per login (browser or app). Shown in Settings → Active sessions with a Revoke button. The access JWT carries this row's id as `sid` `[D-18][D-22]` |
| passkeys | user_id, credential_id, public_key, sign_count, transports, label | WebAuthn credentials, web only in V1 |
| recovery_codes | user_id, code_hash, used_at | 10 per user, one-time use, stored hashed |
| accounts | user_id, institution_name, nickname, type (`checking` / `savings` / `credit` / `cash`), last4, current_balance_cents, import_format (`csv` / `ofx`, null until first import) | Only the last 4 digits, never a full account number. `import_format` is locked by the first import `[D-19]` |
| imports | user_id, account_id, filename, file_type, row_count, imported_count, skipped_duplicate_count, status, file_sha256 | `file_sha256` powers the "already imported this exact file" warning; row-level dedupe prevents duplicates `[D-01]` |
| transactions | user_id, account_id, import_id, posted_on (date), description_raw, merchant, amount_cents, category_id, category_source (`rule` / `ai` / `user`), fitid (nullable), dedupe_hash, is_cash, receipt_id | **Unique on (account_id, dedupe_hash)** `[D-01]` |
| categories | user_id (null = built-in), name_key or custom_name, kind (`expense` / `income` / `transfer`), color | Built-ins have translation keys; custom ones ("Mom") store the user's text |
| category_rules | user_id, match_type (`exact` / `contains` / `regex`), pattern (max 200 chars), category_id, created_from (`user` / `chat`) | Learned from user corrections. Regex compiled with RE2 `[D-08]` |
| bank_csv_mappings | user_id, institution_name, column_map (JSON), delimiter, date_format | Remembered CSV column mapping per bank |
| receipts | user_id, object_key, merchant, total_cents, purchased_on, payment_method, raw_ai_json, status (`draft` / `confirmed`) | Image in R2 under `object_key`, never in the database or on the API's disk `[D-04]` |
| subscriptions | user_id, merchant, typical_amount_cents, cadence_days, next_expected_on, last_seen_on | Rebuilt after each import |
| chat_messages | user_id, role (`user` / `assistant`), content, created_at | Last 50 kept per user |

### 5.1 Deduplication `[D-01]`

Every transaction gets exactly one `dedupe_hash`, and
`UNIQUE (account_id, dedupe_hash)` lets the database itself refuse duplicates.

**Rule A: OFX / QFX with a FITID.**
`dedupe_hash = SHA-256("fitid|" + account_id + "|" + FITID)`; `fitid` is stored.

**Rule B: CSV, and OFX/QFX rows without a FITID.**
`dedupe_hash = SHA-256("row|" + account_id + "|" + posted_on + "|" + amount_cents + "|" + normalized_description + "|" + occurrence_index)`

- `occurrence_index` counts identical rows (same posted_on, amount_cents, normalized_description) within **one file**, in file order: 1, 2, 3…
- `normalized_description` = NFKC, case-folded, whitespace runs collapsed to one space, trimmed; digits kept. Frozen as `normalize_v1`; any change ships as `normalize_v2` with a migration.
- Overlapping statements line up because both files number the same identical rows the same way. Known limit: a description the bank edits between exports counts as new; the preview shows it.

**Format lock** `[D-19]`: Rules A and B give the *same* real transaction
*different* hashes, so mixing CSV and OFX imports on one account would
duplicate every overlapping row. The first import sets
`accounts.import_format` (`ofx` covers OFX and QFX). A later import in the
other format is refused with HTTP 409
`{"error": {"code": "account_format_locked", ...}}`. The translated message
says which format the account uses, and that a different format needs a
separate account. The check runs at preview, before any file is parsed into
rows.

**Import report.** Every confirm returns and shows
"X imported, Y skipped as duplicates"; the counts are stored on `imports`.

---

## 6. Security and privacy

The rule: store the least data possible, encrypt what is sensitive, and send
the AI only what it needs.

### 6.1 Domain, cookies, Origin and CORS `[D-15][D-16][D-17]`

- Web: `https://finance.jonathansewe.com`. API: `https://api.finance.jonathansewe.com`.
- **Same-site is not enough here.** Every `*.jonathansewe.com` host
  (including the resume site and any future project) is the *same site* as
  the API. So `SameSite=Strict` still blocks other websites, but not
  Jonathan's other subdomains. A bug on any of them could make a browser send
  the refresh cookie to the API. The Origin check below closes that gap.
- **Refresh token cookie** (web): `refresh_token`,
  `HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth/refresh`, and
  **never a `Domain` attribute**, so it is host-only on
  `api.finance.jonathansewe.com`. A test inspects every `Set-Cookie` header
  the API can emit and fails if any contains `Domain=`. `[D-17]`
- **Access token:** a 15-minute JWT holding `sub` (user id) and `sid`
  (session id). Web keeps it in memory only. Native keeps the refresh token
  in `expo-secure-store` and sends it in the body of `/auth/refresh`.
- **Origin check** `[D-16]`, in `security/origin.py`, applied as middleware:
  - Applies to `POST /auth/refresh` and to **every** `POST`, `PATCH`, `PUT` and `DELETE`.
  - If an `Origin` header is present, it must exactly equal one entry of `ALLOWED_ORIGINS` (prod: only `https://finance.jonathansewe.com`). Otherwise: 403 `origin_not_allowed`.
  - If `Origin` is missing: allowed only when the request carries **no cookies** and authenticates with an `Authorization: Bearer` header or a refresh token in the body (a native app, which sends no Origin and holds no ambient credentials). A missing Origin with any cookie → 403. Browsers always send `Origin` on these requests, so a browser can't hit this branch.
  - Safe methods (`GET`, `HEAD`, `OPTIONS`) are not checked: they never change state.
- **CORS:** allow exactly the `ALLOWED_ORIGINS` list, with `allow_credentials=True`; never `*`. CORS controls what the browser lets a page *read*. The Origin check controls what the API *accepts*. They are different jobs, so both stay.
- **WebAuthn:** `WEBAUTHN_RP_ID=finance.jonathansewe.com` (not the root), so passkeys belong to this app only. Expected origin `https://finance.jonathansewe.com`.
- **Local development:** `http://localhost:8081` (Expo web) and `http://localhost:8000` (API) are the same site (a site ignores the port). Use Chrome or Firefox (they accept `Secure` cookies on `http://localhost`; Safari does not). `ALLOWED_ORIGINS=http://localhost:8081`, `WEBAUTHN_RP_ID=localhost`.
- **Fallback for Vercel preview URLs** (`*.vercel.app`): `vercel.json` rewrites `/api/:path*` to the API, so the browser sees one origin. Add the preview origin to `ALLOWED_ORIGINS` only on a non-production API. `vercel dev` reproduces this setup locally.

### 6.2 Authentication

1. Sign up with email + password (argon2id). Email verification by a 6-digit code (sent through `services/email.py`), valid 10 minutes, max 5 tries.
2. TOTP two-factor is required before any bank data can be imported. Show a QR code plus 10 one-time recovery codes (stored hashed).
3. Passkeys (WebAuthn) on web: after the first login, offer a passkey; once one exists, it is the default web login.
4. **Active sessions** `[D-22]`: Settings lists every non-revoked session (device summary, last seen, "this session" marker) with a Revoke button. No device cap in V1.
5. Tokens: access JWT 15 minutes; refresh token 30 days, rotated on every use. Reusing an already-rotated refresh token revokes that whole session.
6. **Logout** `[D-18]`: `POST /auth/logout` requires the access token, reads its `sid` claim, and sets `sessions.revoked_at` for that row. Its response also clears the cookie (`Set-Cookie: refresh_token=; Max-Age=0; Path=/api/v1/auth/refresh`, still no `Domain`). The browser applies that header even though the logout request itself never carried the cookie, because a response may set a cookie for any path on its own host. Every authenticated request checks that its `sid` is not revoked, so revoking from Settings works within one request, not after 15 minutes.
7. Rate-limit login, verification, TOTP and recovery endpoints (for example 5 tries per minute per IP and per account).

### 6.3 Data protection

- Never collect or store SSNs, full account numbers, card numbers, or bank passwords. The statement parser keeps only the last 4 digits.
- Encrypt sensitive columns with AES-256-GCM (`cryptography`); key from `DATA_ENCRYPTION_KEY`.
- HTTPS only; HSTS on.
- Uploaded statements are parsed in memory and discarded; only parsed rows and the file's SHA-256 are kept. Nothing user-owned touches the API's local disk.
- Receipt images: private R2 bucket, `receipts/<user_id>/<uuid>.<ext>`, 5-minute signed GET URLs.
- Every query filters by the authenticated `user_id`; every router has a test that user A can't read user B's data.
- Log events, never descriptions, amounts, tokens or email codes.
- Account deletion erases all user rows and every R2 object under the user's prefix in the same request.

### 6.4 What the AI sees

- **Masking first** `[D-09][D-27]`: before any text leaves for the AI, `services/masking.py` replaces person names in transfer descriptions with `[PERSON]`. Patterns covered in V1:
  - Zelle: `Zelle payment to JANE DOE 12345` → `Zelle payment to [PERSON]`
  - Venmo: `VENMO *JOHN SMITH` → `VENMO *[PERSON]`
  - Cash App: `Cash App*Jane Doe` → `Cash App*[PERSON]`
  - PayPal (person-to-person): `PAYPAL *JANEDOE` → `PAYPAL *[PERSON]`. Known merchants after `PAYPAL *` (for example `PAYPAL *NETFLIX`) are kept by an allowlist.
  - Apple Cash: `APPLE CASH SENT MONEY TO JANE DOE` → `APPLE CASH SENT MONEY TO [PERSON]`
  - Generic transfers: `TRANSFER TO JANE DOE`, `TRANSFER FROM J DOE` → `TRANSFER TO [PERSON]`, `TRANSFER FROM [PERSON]`, unless the text after TO/FROM is an account reference (for example `SAVINGS ...1234`).

  The database keeps the original text. The user's own rules run on it before any AI call, so "JANE DOE → Mom" still works.
- Categorization sends only masked descriptions, amount, date and the category list.
- Chat sends the question and the results of report tools the model asks for (7.5), never raw history.
- Receipts send the image only after the user taps Scan.
- Settings shows, in 3 languages: *"SEWE sends the AI only what it needs: masked descriptions to sort transactions, report totals to answer your questions, and a receipt image when you tap Scan. Names of people you pay are replaced with [PERSON]. Your account numbers, passwords and full history never leave our servers."*

---

## 7. Features

### 7.1 Statement import

- Accept `.csv`, `.ofx`, `.qfx` up to 5 MB.
- CSV: auto-detect delimiter and the date, description and amount columns (also split debit/credit columns); if unsure, show a column-mapping step and remember it per bank.
- OFX/QFX: read FITID when present.
- Flow: pick file, choose or create the account, **format-lock check** `[D-19]`, preview the first 20 rows with AI categories and a duplicate flag, confirm, import. Then show "X imported, Y skipped as duplicates".
- If the file's SHA-256 matches an earlier import, warn before the preview.
- After import: categorize, rebuild subscriptions, recompute balances.

### 7.2 Categorization

Run in this order and stop at the first match:

1. The user's own `category_rules` (exact, then contains, then regex), on the unmasked description, on the backend.
2. Built-in keyword rules, **written new in M4** `[D-26]`. P1 had no rules (its CSV was categorized by hand), but P1's sample rows seed the first rules, for example `MTA`, `OMNY`, `LIRR` → Transport, and `AMC` → Entertainment.
3. AI: mask (6.4), then send uncategorized rows in batches of 50 to `AI_MODEL_FAST`. The response must be JSON `[{"id": ..., "category": ...}]` limited to the user's category list, enforced with structured outputs (`output_config.format`). On a schema or validation failure, retry once. Anything still unknown becomes "Uncategorized". `[D-21]`

When the user changes a category, ask "Apply to all from this merchant?" and,
if yes, create a rule. Custom categories: create one ("Mom"), bulk-select
into it, or say it in chat; chat-proposed changes need the user's
confirmation.

**User regex rules** `[D-08]`: compiled with `google-re2` (linear time, no
ReDoS); max 200 characters; invalid, too-long or unsupported patterns
(backreferences, lookaround) are rejected at save with 422 and a translated
error (`rule_pattern_invalid`, `rule_pattern_too_long`,
`rule_pattern_unsupported`); matching is case-insensitive.

### 7.3 Reports

- Periods: day, week, month, year, custom range; filters by account, category, type.
- Views: period total, bar chart by category, trend over the last 6 or 12 periods, top merchants, income vs. spending.
- Subscriptions: same merchant, amount within 10%, interval of 7, 14, 30 or 365 days (±3), seen at least twice.
- Export: CSV of filtered transactions and a PDF report (server-side, `reportlab`).
- `services/reports.py` is the single source of truth for every total; Reports and chat call the same functions.

### 7.4 Receipts

- Camera or photo library. The API stores the image in R2 (`object_key` only in the DB), then sends it to `AI_MODEL_SMART` for JSON: merchant, total, date, payment method, optional line items.
- The user reviews every field. Cash → create a cash transaction; card → offer to match an existing transaction (same amount, date within 3 days).
- Unconfirmed drafts are deleted from R2 after 7 days.

### 7.5 AI chat `[D-07][D-21]`

- **Tool calling.** Tools in `ai/chat_tools.py` wrap `services/reports.py`: `get_period_summary`, `get_spending_by_category`, `get_trend`, `get_top_merchants`, `get_subscriptions`, `get_category_list`. The backend runs them scoped to the authenticated user; the model only phrases results and **never computes totals**.
- Tool results carry `amount_cents` and a locale-formatted `display` string; the model must quote `display`.
- **Grounding check:** every money figure in the answer must appear in that turn's tool results. Otherwise retry once with a correction; if it still fails, show a translated "I couldn't verify that number. Please check the Reports screen."
- **`tool_choice`:** the chat model, `claude-sonnet-5-5`, rejects `tool_choice` `any` and `tool` with a 400 *whatever the thinking settings*. So the request uses `tool_choice: {"type": "auto"}`, tools marked `strict: true`, and the system prompt saying to use the tools. Because `auto` doesn't guarantee a call, the backend checks whether a money question produced a tool call and retries once if not. Source and quote: D-21.
- Answers in the selected language, cite the numbers used, and end money suggestions with the educational-only notice.
- Suggested questions as translated chips. Text input only (voice is V1.1).

### 7.6 Settings

Theme (dark, light, follow system), language (English, Français, Español),
import statement, accounts, export all data (JSON + CSV zip), **active
sessions with Revoke**, passkeys, two-factor, recovery codes (regenerate),
AI provider (SEWE AI; bring-your-own-key shown as "coming soon"), the AI
privacy sentence (6.4), delete account.

---

## 8. API endpoints

All routes live under `/api/v1`, return JSON, and require auth except the
`auth` group (logout needs the access token). FastAPI's `/docs` must stay
accurate. Every POST/PATCH/PUT/DELETE passes the Origin check (6.1).

| Group | Method and path | Purpose |
|---|---|---|
| health | GET `/health` | Liveness + database reachability |
| auth | POST `/auth/signup`, `/auth/verify-email`, `/auth/login`, `/auth/refresh`, `/auth/logout` | Account and session. Logout revokes by `sid` `[D-18]` |
| auth | POST `/auth/totp/setup`, `/auth/totp/verify`, `/auth/recovery/verify`, `/auth/recovery/regenerate` | Two-factor and recovery codes |
| auth | POST `/auth/passkey/register/options`, `/register/verify`, `/login/options`, `/login/verify` | Web passkeys |
| sessions | GET `/sessions`, DELETE `/sessions/{id}` | Active sessions list and revoke `[D-22]` |
| accounts | GET, POST `/accounts`; PATCH, DELETE `/accounts/{id}` | Accounts and balances |
| imports | POST `/imports/preview` (multipart), POST `/imports/{id}/confirm`, GET `/imports` | Two-step import; 409 `account_format_locked` `[D-19]`; confirm returns `{imported, skipped_duplicates}` |
| transactions | GET `/transactions?from&to&account&category&q&page`; PATCH `/transactions/{id}`; POST `/transactions/bulk-categorize`; POST `/transactions/cash` | List, fix, bulk move, cash entry |
| categories | GET, POST `/categories`; PATCH, DELETE `/categories/{id}`; GET, POST, DELETE `/category-rules` | Categories and learned rules |
| reports | GET `/reports/summary`, `/reports/by-category`, `/reports/trend`, `/reports/subscriptions`, `/reports/export?format=csv\|pdf` | Report data and export |
| receipts | POST `/receipts/scan`, PATCH `/receipts/{id}`, POST `/receipts/{id}/confirm`, GET `/receipts/{id}/image-url` | Scan, review, save, signed URL |
| chat | POST `/chat` (streamed), GET `/chat/history`, DELETE `/chat/history` | AI chat |
| settings | GET, PATCH `/settings`; GET `/settings/export`; DELETE `/me` | Preferences, export, delete account |

Errors use one shape: `{"error": {"code": "string", "message": "string"}}`.
Codes are stable keys the app translates.

---

## 9. UI spec `[D-28]`

Match the "Final V1" artboard on the
[SEWE Finance design canvas](https://claude.ai/artifact/HDWwVMWTPbZwk3izVKUvEe):
dark theme from direction B, light theme and reports from direction C,
floating island navigation from C. **Where the canvas and this spec differ,
the spec wins.** The canvas still shows items cut from V1 (the "Lv." pill,
the streak/XP card, "+20 XP" labels, the mic button, PDF in the import
types, "Trusted devices 1 of 3", "Two-factor (SMS + email)"). Leave those
out, and label two-factor "Authenticator app (TOTP)".

**Theme tokens** (`app/theme/tokens.ts`; components read tokens, never raw hex)

| Token | Dark | Light |
|---|---|---|
| bg | #0F1115 | #F3F5FA |
| surface | #191C22 | #FFFFFF |
| line | #262A31 | #E6EAF2 |
| field / fieldLine | #0F1115 / #333842 | #F3F5FA / #E6EAF2 |
| text | #F2F3F5 | #0B1023 |
| muted | #A0A6B1 | #5A6275 |
| chip / chipText | #262A31 / #D4D8DE | #EEF1F7 / #3B4357 |
| accent / accentText / onAccent | #B8F24A / #B8F24A / #0F1115 | #2340D3 / #2340D3 / #FFFFFF |
| accentSoft / accentSoftText | #262A31 / #B8F24A | #E3E8FB / #1A31A8 |
| hero / heroText / heroSub / heroTile | #191C22 / #F2F3F5 / #A0A6B1 / #262A31 | #2340D3 / #FFFFFF / #DDE3FB / rgba(255,255,255,0.14) |
| frame / frameLine | #000000 / #B8F24A | #0B1023 / #8FA2F0 |
| island / islandLine / islandText | #20242B / #2E333B / #A0A6B1 | #0B1023 / #0B1023 / #C9CFE0 |
| islandActive / islandActiveText | #B8F24A / #0F1115 | #2340D3 / #FFFFFF |
| danger | #FF8A7A | #C2261A |

**Type:** Space Grotesk 600–700 for headings and big numbers, Inter 400–600 for body. Sizes: big number 40, title 21, section 16, body 15, small 12–13, nav 10.

**Shape:** cards radius 20–24, pills 999, inputs 12, 8 px grid, touch targets ≥ 44 px.

**Header:** 64 px tall; screen title left (Space Grotesk 700, 21 px); a 44 px round sun/moon theme button right (sun shown in dark, moon in light).

**Navigation:** floating island 12 px from the sides, 16 px from the bottom, 68 px tall, radius 34, 6 px padding, 5 equal tabs (Accounts, Reports, Receipt, AI Chat, Settings), 20 px stroke icons over 10 px bold labels. The active tab is a radius-28 pill in `islandActive`. Content gets 112 px bottom padding. On web wider than 900 px, keep a centered 480 px column.

**Screens**

1. Accounts: empty state (hero "Total balance —", "No data yet" card, Import a statement, Connect a bank → "coming soon"), then hero total with account tiles, Spent and top-custom-category tiles, recent transactions with category chips and "+ Import".
2. Import: file zone (CSV, OFX/QFX), format-lock message when relevant, preview with AI categories and duplicate flags, confirm, import report.
3. Reports: period pills (Day, Week, Month, Year), big total, bar chart by category, subscriptions, export.
4. Receipt: camera frame, Take photo / From Photos, editable AI-read fields, Add to expenses.
5. AI Chat: bubbles, suggestion chips, text input, educational notice.
6. Settings: Appearance (theme, language), Data, Security (active sessions, passkeys, two-factor, recovery codes), AI (provider, privacy sentence), app version.

**Theme switching:** header button plus Settings control; default follows the system; saved to `user_settings` (from M2; device-local before that) and applied instantly.

**Languages:** every visible string from `i18n/en.json`, `fr.json`, `es.json`; a test fails if key sets differ. Money via `Intl.NumberFormat` (`en-US`, `fr-FR`, `es-US`, USD); dates in the same locales; AI answers follow the selected language.

**Accessibility:** WCAG AA contrast in both themes, labels on every icon button, screen-reader names on charts, works with font scaling up to 130%.

---

## 10. Milestones `[D-23][D-24]`

Nine milestones, in order. Each ends with passing tests, a commit, its
`LEARN.md` section and one rewrite exercise.

**Assumptions:** 20 h/week; a beginner in TypeScript, React Native and
FastAPI. "Build" = Claude Code builds, Jonathan reviews, runs and debugs.
"Learn" = the short LEARN.md section plus the exercise.

| # | Milestone | v1.1 h | Build h | Learn h | Total h |
|---|---|---|---|---|---|
| M1 | Skeleton | 12 | 8 | 1.5 | 9.5 |
| M2 | Auth and security | 20 | 13 | 2 | 15 |
| M3 | Import, dedupe, format lock | 16 | 12 | 1.5 | 13.5 |
| M4 | Categorization, RE2, masking | 14 | 10 | 1.5 | 11.5 |
| M5 | Reports | 13 | 10 | 1.5 | 11.5 |
| M6 | Receipts and R2 | 11 | 8 | 1.5 | 9.5 |
| M7 | AI chat with tools | 14 | 9 | 1.5 | 10.5 |
| M8 | Settings and polish | 13 | 7 | 1 | 8 |
| M9 | Ship the web app | 17 | 8 | 1 | 9 |
| | **Subtotal** | 130 | **85** | **13** | **98** |
| | Buffer (+20%) | 32 | | | 20 |
| | **Total** | **162** | | | **≈ 118 h ≈ 6 weeks at 20 h/week** |

Realistic range: **5 to 7 weeks.** M2 (auth) is still the biggest schedule risk.

1. **M1 · Skeleton.** Monorepo; `legacy/` with the P1 script, its data and a README saying the data is invented; FastAPI app with `/health`; Postgres + API via Docker Compose; Alembic set up (empty baseline); Expo app with Expo Router, theme tokens, header with theme toggle, i18n with 3 matching files, island nav with 5 placeholder tabs and a language switcher in Settings; CI running lint + tests; `LEARN.md` and `exercises/M1`.
   - Done when: `docker compose up` + `npm run web` shows the island; switching theme and language works; CI is green.
   - Exercise: `resolveTheme(preference, systemScheme)`.

2. **M2 · Auth and security.** Signup, email code via `services/email.py` (console sender locally, Resend in prod), login, TOTP, recovery codes, web passkeys, refresh rotation with reuse detection, logout by `sid`, active sessions + revoke, Origin middleware, cookie rules, rate limits.
   - Done when: tests cover wrong password, expired code, reused refresh token, logout revoking by `sid`, revoked session rejected on the next request, a used recovery code rejected, CORS rejecting other origins, **Origin check rejecting `https://jonathansewe.com` and a missing Origin with a cookie**, **no `Set-Cookie` containing `Domain=`**, and user A unable to read user B.
   - Exercise: `verify_totp(secret, code, at_time)`.

3. **M3 · Import, dedupe, format lock.** CSV + OFX/QFX parsers, FITID, column mapping, preview, confirm, dedupe (5.1), import report, accounts, balances, transactions list.
   - Done when: a real statement from Jonathan's bank imports; two identical $2.90 OMNY rides on one day are both kept; re-importing a file adds 0 rows; two overlapping files give no duplicates and no losses; OFX dedupes by FITID and falls back to Rule B without it; **a CSV import into an OFX-locked account returns 409 `account_format_locked`, and vice versa**; fixtures use fake data.
   - Exercise: `compute_dedupe_hashes(rows, account_id)`.

4. **M4 · Categorization.** User rules, built-in rules seeded from P1's sample rows, AI batches with structured outputs, corrections → rules, custom categories, bulk move, RE2, masking.
   - Done when: ≥ 85% of fixture rows land in the right category; a merchant correction re-categorizes its other rows; RE2 rejects a 201-char pattern and a lookahead, and never hangs; **no fixture person name (Zelle, Venmo, Cash App, PayPal, Apple Cash, TRANSFER TO/FROM) reaches the AI mock**, while `PAYPAL *NETFLIX` is kept; AI calls mocked.
   - Exercise: `categorize(row, user_rules, builtin_rules)`.

5. **M5 · Reports.** Summary, by category, trend, subscriptions, CSV and PDF export, Reports screen.
   - Done when: numbers match a hand-computed fixture to the cent; the chart renders in both themes.
   - Exercise: `detect_subscriptions(transactions)`.

6. **M6 · Receipts.** Camera and library, R2 upload and signed URLs, AI extraction, review form, cash transactions, card matching, draft cleanup.
   - Done when: a real receipt photo fills merchant, total and date; confirming creates one transaction; nothing is written to local disk; account deletion removes the user's R2 objects (tested with an S3 mock).
   - Exercise: `match_receipt_to_transaction(receipt, candidates)`.

7. **M7 · AI chat.** Report tools, tool loop with `auto` + strict tools + missing-call retry, grounding check, streaming, history, suggestion chips.
   - Done when: in CI (recorded model), every money figure in the fixture answers equals Reports to the cent; an invented number is caught by the grounding check; **a manual live-model eval of ~20 questions passes** (approved, < $1, D-29).
   - Exercise: `find_ungrounded_amounts(answer_text, tool_results)`.

8. **M8 · Settings and polish.** Full Settings (sessions, passkeys, recovery codes, export, delete account), empty, loading and error states.
   - Done when: every string is translated in all 3 languages; delete account leaves no rows and no R2 objects.
   - Exercise: `build_export_bundle(user_data)`. Its tests check the zip holds JSON and CSV, amounts are in cents, and another user's rows are never included.

9. **M9 · Ship the web app.** DNS (`finance`, `api.finance`), deploy API (Render), database (Neon), web (Vercel); Resend domain verification (SPF/DKIM on `jonathansewe.com`); production env vars; nightly backup workflow + heartbeat alert `[D-20]`; README with screenshots; privacy policy page.
   - Done when: Jonathan uses `https://finance.jonathansewe.com` on his phone with his own statement; one backup has been restored into a scratch Neon branch; **the heartbeat alert fires in a test when a ping is skipped**.
   - Exercise: `validate_production_settings(settings)`.

---

## 11. Testing, CI, deployment

### 11.1 Tests

- Backend: `pytest` with a throwaway Postgres; ≥ 80% coverage on `services/` and `security/`. Every AI call is mocked with recorded fixtures (except the manual M7 eval). R2 mocked (`moto`). Email uses the console sender.
- Frontend: Jest + React Native Testing Library; one Playwright smoke test on the web build (added in M3: sign up, import fixture CSV, see the Reports total).
- Fixtures use invented merchants, amounts and names. Never commit a real statement.

### 11.2 CI (GitHub Actions, every push and pull request)

1. Backend: `ruff`, `mypy`, `pytest`.
2. Frontend: `eslint`, `tsc --noEmit`, `jest`, i18n key-parity check.
3. Exercises: run the reference solutions against the exercise tests, so the tests themselves stay correct.
4. Block the merge if any step fails.

### 11.3 Deployment

- Environments: `local` and `prod`. Migrations run on deploy (`alembic upgrade head`).
- Env vars: `DATABASE_URL`, `JWT_SECRET`, `DATA_ENCRYPTION_KEY`, `ANTHROPIC_API_KEY`, `AI_MODEL_FAST`, `AI_MODEL_SMART`, `EMAIL_PROVIDER` (`console` / `resend`), `RESEND_API_KEY`, `EMAIL_FROM`, `ALLOWED_ORIGINS`, `WEBAUTHN_RP_ID`, `WEBAUTHN_ORIGIN`, `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `COOKIE_SECURE`.
- Monthly spend cap on the AI key; per-user daily limits on chat and receipt calls.

### 11.4 Backups and the heartbeat alert `[D-03][D-20]`

- Nightly GitHub Actions job: `pg_dump --format=custom`, encrypt, upload to a private R2 bucket (`sewe-backups`), keep 14 nightly + 8 weekly.
- **The risk:** in a public repo, GitHub disables scheduled workflows after 60 days with no repository activity, and the backups would stop silently.
- **The alert (dead man's switch):** the last step of a *successful* backup pings a Healthchecks.io check (free Hobbyist plan) set to period 1 day, grace 1 day. If no ping arrives for 48 hours, for any reason (workflow disabled, dump failed, R2 down), Healthchecks.io emails Jonathan. The alert lives outside GitHub on purpose: a checker inside GitHub would be disabled along with the job it watches. The ping URL is a secret (`HEALTHCHECK_BACKUP_URL`).
- Restore is tested once in M9.

### 11.5 Monthly costs `[D-11]`

| Item | Cost |
|---|---|
| Domain `jonathansewe.com` | already owned (shared) |
| Vercel Hobby, Neon Free, R2 free tier, Resend free (3,000/month, 100/day, 1 domain), Healthchecks.io Hobbyist | $0 |
| Render API | $0 free (sleeps after 15 min, ≈ 1 min cold start) or $7 Starter |
| AI (one heavy user) | ≈ $2.30 |
| **Total** | **≈ $2.30/month free setup, ≈ $9.30 with Render Starter** |

---

## 12. Teaching deliverables `[D-24]`

Short by design. Each milestone produces two things.

### 12.1 `LEARN.md` section (repo root), about one screen long

```
## M<n> · <name>
What we built: 2–3 sentences.
Files: one line per key file — what it does.
New concepts: up to 3, one sentence each, with where they appear.
Commands: the ones used, each with a one-line explanation.
Try it: one small change to make yourself.
```

### 12.2 Rewrite exercise (`exercises/M<n>/`)

- `README.md` (≤ 20 lines): the signature, what it must do, edge cases.
- Tests for Jonathan's version (`my_<function>.*`), shared with a reference solution that CI also runs.
- Run with one command, given in the README.

| Milestone | Function |
|---|---|
| M1 | `resolveTheme(preference, systemScheme)` (TypeScript) |
| M2 | `verify_totp(secret, code, at_time)` |
| M3 | `compute_dedupe_hashes(rows, account_id)` |
| M4 | `categorize(row, user_rules, builtin_rules)` |
| M5 | `detect_subscriptions(transactions)` |
| M6 | `match_receipt_to_transaction(receipt, candidates)` |
| M7 | `find_ungrounded_amounts(answer_text, tool_results)` |
| M8 | `build_export_bundle(user_data)` |
| M9 | `validate_production_settings(settings)` |

Written for a computer science student who knows Python basics and is new to
TypeScript, React Native and FastAPI.

---

## 13. V1.1 (after V1 ships) `[D-22]`

Cut from V1 to ship faster. Each is designed already; the decisions still apply.

| Feature | Notes carried over |
|---|---|
| Native passkeys | Expo dev build, `apple-app-site-association` and `assetlinks.json` served from `finance.jonathansewe.com` (the RP ID). See D-05. |
| EAS builds | `eas build` profiles for iOS and Android. |
| App stores | Apple Developer ($99/yr), Google Play ($25 once); Play needs a 12-tester closed test for 14 days; privacy policy, data-safety form, screenshots in both themes, a reviewer demo account that can pass TOTP. |
| Voice input | Optional, feature-detected, mic hidden when unsupported, no audio to the server. See D-10. |
| PDF import | `pdfplumber` text extraction, AI turns lines into rows, preview always shown. |
| Gamification | XP (+50 first import of a month, +20 per receipt, +10 per day opened, +15 per correction), level = floor(XP/500)+1, badges "First import", "7-day streak", "10 receipts". |
| 3-device cap | Device = one session record; at the cap, password + TOTP or a recovery code grants a list-and-revoke-only session. See D-06. |

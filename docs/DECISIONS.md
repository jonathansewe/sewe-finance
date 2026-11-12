# Decisions

Every judgment call, dated. Format: **Decision**, **Reason**, **Rejected
alternative**. Tags like `[D-01]` in `docs/SPEC.md` point here.

Prices and plan limits were checked on 2026-11-06 from the providers' own
pages where possible, and from recent third-party summaries otherwise. They
change often, so re-check them before paying for anything.

---

## D-01 · Deduplicate by FITID, else by an occurrence-indexed row hash
*2026-11-06 · changes the schema · SPEC 5, 5.1, 7.1, M3*

**Decision.**
- OFX/QFX: the bank's `FITID` is the unique key: `dedupe_hash = SHA-256("fitid|" + account_id + "|" + FITID)`. If a row has no FITID, use the CSV rule.
- CSV: `dedupe_hash = SHA-256("row|" + account_id + posted_on + amount_cents + normalized_description + occurrence_index)`, where `occurrence_index` numbers identical rows 1, 2, 3… in file order within one file.
- `UNIQUE (account_id, dedupe_hash)` in the database (was `UNIQUE (user_id, dedupe_hash)`).
- Every import reports "X imported, Y skipped as duplicates"; counts are stored on `imports`.
- `normalize_v1` is frozen (NFKC, casefold, collapse whitespace, trim; digits kept).
- Required tests: two identical $2.90 OMNY rides on one day are both kept; re-importing a file adds 0 rows; two overlapping files give no duplicates and no losses.

**Reason.** The v1.0 hash (`account_id + posted_on + amount_cents + description`)
gave two genuinely different transactions the same key whenever they matched
on all four fields, for example two subway rides on the same day. The second
one was silently dropped as a "duplicate", which made the totals wrong. FITID
is the bank's own answer to "which transaction is this?", so it is the most
reliable key when it exists. When it doesn't, numbering identical rows within
a file keeps them apart, and overlapping files still line up, because both
files number the same identical rows the same way. The unique constraint
makes the database enforce this, so an application bug can't create
duplicates. Freezing the normalizer matters because any change to it changes
every hash.

**Rejected alternatives.**
- *Keep the v1.0 hash:* loses real transactions.
- *File-level dedupe only (`file_sha256`):* catches only byte-identical re-uploads. Overlapping statements would still duplicate rows. `file_sha256` stays, but only as a warning.
- *Treat every row as new and ask the user to resolve duplicates:* moves the system's job onto the user, and they will make mistakes.
- *Include the row's line number in the file:* line numbers shift between two exports of overlapping periods, so overlaps would duplicate.

---

## D-02 · One domain: `app.<domain>` and `api.<domain>`; strict cookie and CORS
*2026-11-06 · SPEC 1, 3, 6.1, 11.3*

> **Status (v1.2): amended by D-15, D-16, D-17.** Hosts are now `finance.jonathansewe.com` / `api.finance.jonathansewe.com`, RP ID is `finance.jonathansewe.com`, and an Origin check is added because SameSite no longer separates Jonathan's projects.

**Decision.**
- Buy one domain. Web at `https://app.<domain>` (Vercel), API at `https://api.<domain>` (Render).
- Web refresh token in an `HttpOnly; Secure; SameSite=Strict` cookie, host-only on `api.<domain>`, `Path=/api/v1/auth/refresh`. Access token in memory only. Native keeps tokens in `expo-secure-store`.
- CORS allows only `https://app.<domain>`, with credentials.
- `WEBAUTHN_RP_ID` = the root domain.
- Fallback: a Vercel rewrite of `/api/:path*` to the API, for preview deployments and for the time before the domain exists. Local dev works without it (see below).

**Reason.** The browser decides whether to send a `SameSite=Strict` cookie by
comparing *sites* (scheme + registrable domain). `*.vercel.app` and
`*.onrender.com` are both on the Public Suffix List, so `x.vercel.app` and
`y.onrender.com` are different sites. The refresh cookie would never reach
the API, and users would be logged out every 15 minutes. Under one domain,
`app.` and `api.` are the same site, so Strict works, and Strict is also the
strongest CSRF defense cookies offer. CORS with credentials cannot use `*`,
and allowing one exact origin is the safe setting anyway. WebAuthn binds
passkeys to an RP ID. Using the root domain lets `app.<domain>` and the
native apps in M9 share one set of passkeys.

**On the local-dev fallback (a correction to the request).** The request said
"fallback for local dev: Vercel rewrites proxying /api". Rewrites run only on
Vercel's servers, or locally under `vercel dev`; plain `npm run web` ignores
`vercel.json`. They also aren't needed locally, because `localhost:8081` and
`localhost:8000` are the **same site** (a site ignores the port). Chrome and
Firefox accept `Secure` cookies on `http://localhost`. The spec therefore
documents three cases: local dev works as-is (CORS origin
`http://localhost:8081`); `vercel dev` reproduces the rewrite setup on a
laptop if wanted; and the rewrite is the real fallback for Vercel preview
URLs. See OPEN_QUESTIONS Q2.

**Rejected alternatives.**
- *Default host URLs (`*.vercel.app` + `*.onrender.com`) with `SameSite=None`:* works, but gives up Strict's CSRF protection and adds a CSRF-token system to build and test. It also does nothing for the WebAuthn RP ID, which still needs a real domain.
- *Refresh token in `localStorage`:* any XSS bug could steal a 30-day credential.
- *Rewrites as the main production setup (no `api.` subdomain):* every API request would make an extra hop through Vercel and count against Hobby bandwidth. Kept as the fallback only.

---

## D-03 · Database on Neon Postgres, with our own nightly backups
*2026-11-06 · SPEC 3, 11.4*

**Decision.** Use **Neon** Postgres (free plan to start). Do **not** use
Render's free Postgres. Backups: a nightly GitHub Actions job runs
`pg_dump --format=custom`, encrypts it, and uploads it to a private R2 bucket
(`sewe-backups`), keeping 14 nightly and 8 weekly dumps. Restore is tested
once in M9 and after schema-heavy milestones.

**Free-tier limits, as checked on 2026-11-06:**

| | Neon Free | Supabase Free | Render Free Postgres |
|---|---|---|---|
| Storage | 1 GB per project (20 GB across all projects) | 500 MB database | 1 GB |
| Compute | 100 compute-unit-hours per project per month (≈ 400 h at 0.25 CU); suspends after 5 min idle, wakes on the next query | Shared | Shared |
| Inactivity | Compute suspends; data stays, project stays | **Project paused after 1 week of inactivity** | — |
| Lifetime | No expiry | No expiry | **Expires 30 days after creation; deleted after a 14-day grace period** |
| Backups | Short point-in-time restore window only | **No automatic backups on Free** | None |
| Over the limit | Writes that grow storage fail; no surprise bill | Read-only mode | — |

Sources: Neon's free-plan FAQ (updated 2026-10-01), Supabase's pricing page,
Render's free-tier docs and its 2024-05-20 changelog entry.

**Reason.** Render's free database deletes itself after 44 days, which is fatal
for an app holding a user's financial history. Between Neon and Supabase,
Neon has twice the storage and doesn't pause the project after a quiet week.
Its compute suspend costs only a short wake-up delay. Supabase is also a full
backend platform, and the spec already rejected "Supabase only" because it
hides the backend skills this project exists to show. Neither free tier gives
real backups, so the backup plan has to be our own. Keeping dumps in R2 also
means a provider problem can't take the backups down with the database.

**Rejected alternatives.**
- *Render free Postgres:* deleted after 30 + 14 days.
- *Supabase free:* pauses after 1 week idle (likely during exam weeks), 500 MB, no backups.
- *Rely on the provider's restore history as the backup:* too short on free plans, and it lives inside the same provider.
- *Paid Render Postgres:* ≈ $6/mo for what Neon gives free at this size.

---

## D-04 · Receipt images in Cloudflare R2, never on the API's disk
*2026-11-06 · SPEC 3, 5, 6.3, 7.4, 8*

**Decision.** Receipts go to a **private** Cloudflare R2 bucket
(S3-compatible, accessed with `boto3`) under `receipts/<user_id>/<uuid>.<ext>`.
The database stores only `object_key` (replacing `image_url`). The app gets
5-minute signed GET URLs from `GET /receipts/{id}/image-url`. Unconfirmed
drafts are deleted after 7 days. Account deletion removes the user's prefix.
Uploaded statements are also never kept on local disk.

**Reason.** Free and small hosts (including Render's free web service) have an
ephemeral filesystem: files written to local disk vanish on every restart,
deploy or spin-down. R2's free tier covers 10 GB-months of storage, 1 M write
operations and 10 M read operations per month, with **no egress fees**, so
showing images costs nothing. It speaks the S3 API, so the code and the skill
carry over to AWS S3. A private bucket plus short-lived signed URLs means a
leaked URL stops working within minutes.

**Rejected alternatives.**
- *Local disk:* data loss on restart.
- *Images as blobs in Postgres:* eats the 1 GB Neon limit and slows backups.
- *AWS S3:* same API but charges for egress, and its free tier is time-limited.
- *Public bucket:* anyone with a URL could see receipts forever.

---

## D-05 · M2 passkeys on web only; native passkeys move to M9
*2026-11-06 · SPEC 2, 6.2, 8, M2, M9*

> **Status (v1.2): amended by D-22.** Web passkeys stay in M2; native passkeys move out of V1 entirely, to V1.1.

**Decision.** In M2, passkeys work on **web only**. iOS and Android sign in
with password + TOTP. Native passkeys (Expo dev build,
`apple-app-site-association`, `assetlinks.json`) move to M9.

**Reason.** Native passkeys can't run in Expo Go. They need a custom dev build,
a native passkey module, and domain-association files served from the real
domain over HTTPS, and that domain only exists from M9 (D-02). Doing that in
M2 would block the whole auth milestone on deployment work. Web passkeys run
on `localhost` with nothing extra. Native users are still protected by TOTP
in the meantime.

**Rejected alternatives.**
- *All platforms in M2:* M2 blocked on M9 infrastructure, roughly +8–10 h in the hardest milestone.
- *Drop passkeys from V1:* they are a strong resume point and are already half-built by the end of M2.

---

## D-06 · Device = one browser session record; recovery path at the 3-device cap
*2026-11-06 · SPEC 5, 6.2, 8, 9, M2*

> **Status (v1.2): superseded by D-22.** The 3-device cap and `device_management` flow move to V1.1; V1 has an active-sessions list with Revoke.

**Decision.** On web, one device = one browser session record (`devices` row
plus its refresh session). At the cap of 3, a 4th login needs password **and**
TOTP or one unused recovery code. It then gets a `device_management` session,
which may only list and revoke devices. After revoking one, a full session is
issued. Revoking a device deletes its sessions and passkeys.

**Reason.** A browser has no stable hardware ID, and fingerprinting is
unreliable and privacy-hostile. So "device" has to mean the session record.
The side effect is that clearing cookies or opening a private window makes a
new device, which could lock a user out at the cap. Requiring a second factor
before showing the device list keeps an attacker with only the password from
kicking out the real user's devices. The restricted session scope keeps that
half-logged-in state from being able to read any financial data.

**Rejected alternatives.**
- *Hard refusal at the cap (v1.0 wording):* locks users out of their own data after a cookie wipe.
- *Auto-evict the oldest device:* an attacker with the password silently logs out the real user.
- *Browser fingerprinting:* unreliable, and contradicts "store the least data possible".
- *Recovery by email link only:* turns email into a bypass of TOTP.

---

## D-07 · AI chat uses tool calling; the model never computes totals
*2026-11-06 · SPEC 6.4, 7.3, 7.5, M7*

> **Status (v1.2): corrected by D-21.** The forced-`tool_choice` limit is model-specific (Sonnet 5.5 is affected; Haiku 5.5 is not), not "current Claude models" in general.

**Decision.** The chat model gets tools that wrap `services/reports.py`
(period summary, by category, trend, top merchants, subscriptions, category
list). It calls them, the backend runs them for the authenticated user, and
the model only phrases the results. Tool results include integer cents plus
a pre-formatted `display` string the model must quote. A grounding check
rejects any answer containing a money figure not in that turn's tool results.
Tools use `strict: true` with `tool_choice: auto`. Test: chat figures equal
the Reports screen to the cent.

**Reason.** Language models are good at choosing which numbers matter and
explaining them, and unreliable at arithmetic over many rows. With v1.0's
"compact summary" approach, the model would sometimes add up the wrong
numbers, or round, or invent one. Routing every number through the same
functions as the Reports screen means the two can't disagree. The `display`
string stops locale reformatting errors (`12.40` vs `12,40`). The grounding
check catches the remaining failure, a made-up number. Current Claude models
(Sonnet 5.5 included) return a 400 on forced `tool_choice` (`any`/`tool`),
so the spec uses `auto` and steers from the system prompt.

**Rejected alternatives.**
- *Precomputed summary in the prompt (v1.0):* the model still does arithmetic to combine figures, and the summary has to guess in advance which numbers a question needs.
- *Let the model write SQL:* a security hole (cross-user reads, injection) and hard to test.
- *Code-execution tool:* the model would need raw data, which breaks the privacy rules in 6.4.

---

## D-08 · User regex rules run on google-re2, max 200 characters
*2026-11-06 · SPEC 4, 5, 7.2, M4*

**Decision.** Compile user regex rules with `google-re2` (`import re2`),
never Python's `re`. Patterns are at most 200 characters. Invalid,
over-length or unsupported patterns are rejected at save time with HTTP 422
and a clear, translated error (`rule_pattern_invalid`,
`rule_pattern_too_long`, `rule_pattern_unsupported`).

**Reason.** Python's `re` uses backtracking, so a pattern like `(a+)+$`
against a long string can take exponential time and freeze the API worker
(ReDoS). RE2 guarantees linear-time matching by design, so no timeout hack
is needed. The cost is that RE2 doesn't support backreferences or
lookaround, which nobody needs to match a merchant name; the error message
says so. A length cap bounds memory and keeps rules readable. Checking at
save time means a bad rule never reaches the import pipeline.
*Verify in M4 that `google-re2` installs from a prebuilt wheel on Python 3.12
on the CI and Render images.*

**Rejected alternatives.**
- *Python `re` with a timeout:* `re` has no timeout. Running each match in a subprocess or thread to kill it is slow and complicated.
- *The `regex` package's `timeout=`:* works, but still backtracks, and a timeout limits the damage rather than preventing it.
- *No regex rules at all:* exact/contains cover most cases, but regex is in the v1.0 scope.

---

## D-09 · Mask person names in P2P transfer descriptions before any AI call
*2026-11-06 · SPEC 4, 6.4, 7.2, M4*

**Decision.** `services/masking.py` replaces person names in Zelle, Venmo and
Cash App descriptions with `[PERSON]` before **any** text goes to the AI.
The database keeps the original. User rules run on the unmasked text, on the
backend, before the AI step. The Settings privacy sentence now mentions
masking. A test asserts that no fixture person's name ever reaches the AI
mock.

**Reason.** Transfer lines like "Zelle payment to JANE DOE" carry the names of
third parties who never agreed to share data with an AI provider. The
category of a P2P transfer doesn't depend on the name ("Zelle to [PERSON]"
is clearly a transfer). Where the name *does* matter ("JANE DOE" means
"Mom"), the user's own rule already handles it locally, without the AI.
Pattern-based masking for known P2P formats is predictable and testable.

**Rejected alternatives.**
- *Send descriptions as-is (v1.0):* leaks third-party names.
- *NER/ML name detection on every description:* heavy dependency, unpredictable, and it would mask merchant names like "Dos Toros" too.
- *Skip AI for all P2P rows:* loses useful splits (transfer vs. rent paid by Zelle). Masking keeps the signal and drops the name.

---

## D-10 · Voice input is optional and feature-detected
*2026-11-06 · SPEC 2, 4, 7.5, 9, M7*

> **Status (v1.2): moved to V1.1 by D-22.** The design below still applies when voice is built.

**Decision.** Voice is optional. `lib/features.ts` checks for speech
recognition at runtime (`expo-speech-recognition` on native, Web Speech API
on web). If it's unsupported, the mic button is **hidden**, and text chat
works normally. Audio never reaches the server.

**Reason.** The Web Speech API is missing in Firefox and patchy elsewhere, and
`expo-speech-recognition` is a third-party native module that needs a dev
build (not Expo Go). A button that does nothing when tapped looks broken.
Hiding it is honest, and feature detection (instead of browser sniffing)
keeps working as support changes.

**Rejected alternatives.**
- *Disabled button with a tooltip:* clutter, and tooltips barely exist on touch screens.
- *Server-side transcription:* sends audio off-device, which breaks the V1 privacy rule and adds cost.
- *Drop voice:* it's cheap once feature-detected and demos well.

---

## D-11 · Add a monthly cost table
*2026-11-06 · SPEC 11.5*

> **Status (v1.2): updated in SPEC 11.5.** The domain is already owned, so the free setup is ≈ $2.30/month.

**Decision.** Section 11.5 lists monthly costs for two setups. The
**free-tier setup is ≈ $3.30/mo** (domain + AI). The **small paid setup is
≈ $10.30/mo** (adds Render Starter at $7 for an always-on API). The AI key's
spend cap is set at $10/mo. Recommendation: develop on free and move the API
to Starter once anyone besides Jonathan uses it.

**Prices used (2026-11-06):** Claude Haiku 5.5 $0.10 input / $0.50 output per
million tokens (prompts ≤ 100K tokens); Claude Sonnet 5.5 $2 / $10. Render
Starter $7/mo, Hobby workspace $0. Render free web services sleep after
15 min idle, about 1 min to wake. Neon free $0 (D-03). R2 free tier
(D-04). Vercel Hobby $0, personal non-commercial use only. Domain ≈ $10–15/yr.
AI usage assumed: ~300 transactions, 100 chat questions, 30 receipts per month.

**Reason.** Free tiers have catches (cold starts, non-commercial clauses,
deletion policies). Writing the costs down turns "free hosting" into a
choice with known trade-offs, and the AI line shows that Sonnet chat, not
categorization, is what costs money.

**Rejected alternatives.**
- *All-free with no table:* hides the cold start, which is the biggest UX cost.
- *Everything paid from day one (≈ $30+/mo with Vercel Pro):* nothing to pay for yet.

---

## D-12 · Re-estimate the timeline: ≈ 162 h ≈ 8 weeks
*2026-11-06 · SPEC 10*

> **Status (v1.2): superseded by D-23** (≈ 118 h ≈ 6 weeks after the V1 cuts).

**Decision.** Each milestone is re-estimated for a beginner in TypeScript,
React Native and FastAPI, working 20 h/week. Build 106 h + learning 24 h +
25% buffer = **≈ 162 h ≈ 8 weeks**, realistic range 7–10 weeks (v1.0 said
40 h).

**Reason.** The v1.0 estimate assumed someone fluent in the stack. A beginner
loses time to toolchain setup (Docker, Expo, CI), to reading unfamiliar code
before approving it, and to debugging the parts that touch outside systems:
WebAuthn, cookies and CORS, EAS builds, store accounts. The v1.1 patches also
add scope: the device-cap flow, the grounding check, R2, masking, backups,
native passkeys in M9. And learning time (LEARN.md, rewrite exercises) is
real work that the old plan didn't count. A 25% buffer is standard for a
first project on a new stack.

**Rejected alternatives.**
- *Keep 40 h:* sets up every milestone to "fail" its estimate, which hurts motivation and planning.
- *Cut scope to fit 40 h:* not requested. If time is tight, the cheapest cuts are PDF import (stretch), voice, and native passkeys (could slip past V1).

---

## D-13 · LEARN.md sections and one rewrite-yourself function per milestone
*2026-11-06 · SPEC 1, 4, 10, 11.1, 12*

> **Status (v1.2): amended by D-24.** `docs/explain/` is dropped; LEARN.md sections are about one screen; M8's exercise changes because gamification was cut.

**Decision.** Each milestone adds (1) a `LEARN.md` section at the repo root
with a plain-English description of every key file, and (2) one key function
that Jonathan rewrites himself in `exercises/M<n>/`, graded by the same tests
as the real function. The functions are listed in SPEC 12.3. The "file by
file" part of `docs/explain/M<n>.md` moves into `LEARN.md` so the two don't
repeat each other.

**Reason.** Reading code you didn't write feels like understanding until you
try to write it. Rewriting one important function per milestone, against
tests that already exist, is active recall with instant feedback. LEARN.md is
the quick map ("what is this file for?"); `explain/` stays the deep
walkthrough. Each function was picked because it is central to its milestone,
small enough to rewrite in an hour or two, and fully testable without a
network.

**Rejected alternatives.**
- *Put everything in `explain/M<n>.md`:* a long file per milestone with no single map of the repo.
- *Rewrite whole files:* too big; becomes copy-paste.
- *Exercises without tests:* no way to know if the rewrite is right.

---

## D-14 · Supporting details added while applying D-01 to D-13
*2026-11-06*

These were not in the patch list. Each one is needed to make a patch work or
was a gap the patch exposed. They are listed so nothing changed silently.

| Addition | Needed by |
|---|---|
| `recovery_codes` table; `/auth/recovery/verify` and `/regenerate` endpoints | D-06 (recovery code at cap) |
| `sessions.scope` (`full` / `device_management`); device-limit screen | D-06 |
| `devices.kind`, `user_agent_summary`; `passkeys.transports` | D-05, D-06 |
| Reusing a rotated refresh token revokes that device's session family | D-02 (standard rotation safety; M2 test already covered reuse) |
| `bank_csv_mappings` table | v1.0 7.1 said "remember the mapping per bank" but had no table |
| `imports.imported_count`, `skipped_duplicate_count` | D-01 report |
| `user_settings.theme` gains `system` | v1.0 7.6 offered "follow system" but the column had only dark/light |
| `GET /receipts/{id}/image-url`; 7-day draft cleanup; `storage.py` | D-04 |
| Env vars `WEBAUTHN_ORIGIN`, `COOKIE_SECURE`, `R2_*` | D-02, D-04 |
| `ai/chat_tools.py`, `services/masking.py`, `services/dedupe.py`, `lib/features.ts` | D-07, D-09, D-01, D-10 |
| App-store reviewers need a TOTP-capable demo account | D-05 (no passkeys on native until M9) + v1.0 TOTP rule |
| Architecture diagram redrawn as text | v1.0 diagram was an image in the PDF |

---

# v1.2 decisions (Jonathan's answers, V1 cuts, security fixes)

## D-15 · Hosts under `jonathansewe.com`; passkeys scoped to the app
*2026-11-06 · Q1 · SPEC 1, 3, 6.1, 9, 11.3*

**Decision.** `jonathansewe.com` is the resume site (Netlify, not in this repo);
`finance.jonathansewe.com` is the SEWE Finance web app (Vercel);
`api.finance.jonathansewe.com` is the API (Render). DNS is on Cloudflare.
`WEBAUTHN_RP_ID=finance.jonathansewe.com`. Every `app.<domain>` /
`api.<domain>` placeholder is replaced.

**Reason.** One domain shared across projects is cheaper and builds one
personal brand. Setting the RP ID to the app's own host (not the root) means
a passkey made here can only ever be used by SEWE Finance; no other project
on `jonathansewe.com` can request it. Nesting the API under `finance.`
groups the app's hosts and keeps `api.jonathansewe.com` free for other uses.

**Rejected alternatives.**
- *RP ID = `jonathansewe.com`:* any current or future subdomain could use SEWE passkeys.
- *A separate domain just for SEWE:* another yearly fee and DNS zone for no security gain over the Origin check (D-16).

---

## D-16 · Check the `Origin` header on refresh and every state-changing request
*2026-11-06 · security fix 1 · SPEC 6.1, 8, M2*

**Decision.** Middleware in `security/origin.py` checks `POST /auth/refresh`
and every `POST`, `PATCH`, `PUT` and `DELETE`. A present `Origin` must exactly
match `ALLOWED_ORIGINS` (prod: only `https://finance.jonathansewe.com`), or the
request gets 403 `origin_not_allowed`. A **missing** `Origin` is accepted only
when the request has **no cookies** and authenticates with a Bearer token or
a body refresh token (a native client). Safe methods are not checked.

**Reason.** "Same site" means same registrable domain, and every
`*.jonathansewe.com` host shares one. So `SameSite=Strict` stops `evil.com`
but not the resume site, or a future side project with an XSS bug: a page
there could make the browser POST to `/auth/refresh` *with* the cookie. The
`Origin` header names the exact scheme + host + port that started the
request. Browsers set it themselves, and page scripts can't forge it, so an
exact match is a precise allowlist. The missing-Origin rule follows from
what CSRF needs: an attacker needs the victim's *ambient* credentials
(cookies). A request with no Origin and no cookies can't be a browser-driven
CSRF, so native apps work without weakening anything.

**Rejected alternatives.**
- *Rely on SameSite alone (v1.1):* no protection between Jonathan's own subdomains.
- *CSRF tokens (double-submit):* more code and state, for protection the Origin check already gives on modern browsers.
- *Reject every missing Origin:* breaks the Expo native client in development.
- *Check only `/auth/refresh`:* that's the only cookie-authenticated route today, but checking all unsafe methods is cheap and protects any cookie-based route added later.

---

## D-17 · Never set a cookie `Domain` attribute; a test enforces it
*2026-11-06 · security fix 2 · SPEC 6.1, M2*

**Decision.** No cookie the API sets ever carries `Domain=`. A test collects
every `Set-Cookie` header from the auth flows (login, refresh, logout) and
fails if any contains `domain=` (case-insensitive).

**Reason.** Without `Domain`, a cookie is *host-only*: the browser returns it
only to `api.finance.jonathansewe.com`. With `Domain=jonathansewe.com`, the
browser sends it to **every** subdomain, including the Netlify resume site,
and any of them could also overwrite it. That would undo D-15's isolation.
It's a one-word mistake that is easy to make (many tutorials set `Domain`
"so it works across subdomains"), so a test is the right guard.

**Rejected alternatives.** *Code review only:* the mistake is invisible in a diff
unless you know to look for it.

---

## D-18 · Logout revokes the session by the `sid` claim in the access token
*2026-11-06 · security fix 3 · SPEC 5, 6.2, 8, M2*

**Decision.** Access JWTs carry `sid`, the `sessions` row id. `POST /auth/logout`
requires the access token, sets `revoked_at` on the row named by `sid`, and
returns `Set-Cookie: refresh_token=; Max-Age=0; Path=/api/v1/auth/refresh`.
Every authenticated request checks that its `sid` isn't revoked.

**Reason.** The refresh cookie is scoped to `Path=/api/v1/auth/refresh`, so the
browser never sends it to `/auth/logout`, and the server can't identify the
session from the cookie there. The access token *is* sent, so it carries
the session id. A response can still clear the cookie, because a
`Set-Cookie` may name any path on its own host. Checking `sid` on every
request makes logout and "Revoke" take effect immediately instead of when
the 15-minute access token expires. The cost is one indexed lookup per
request.

**Rejected alternatives.**
- *Widen the cookie path to `/api/v1/auth`:* the long-lived credential would then be sent to more endpoints than needed.
- *Logout only deletes the cookie client-side:* the refresh token stays valid on the server for 30 days.
- *Purely stateless JWTs (no `sid` check):* a revoked session keeps working for up to 15 minutes.

---

## D-19 · Lock each account to its first import format
*2026-11-06 · security fix 4 · SPEC 5, 5.1, 7.1, 8, M3*

**Decision.** `accounts.import_format` (`csv` or `ofx`; QFX counts as `ofx`) is
set by the first import. An import in the other format is refused at
preview with 409 `account_format_locked` and a translated message.

**Reason.** Dedupe Rule A hashes the FITID and Rule B hashes the row's
content, so the same real transaction gets two different hashes. An OFX
import followed by an overlapping CSV import would duplicate every
overlapping row, and the unique constraint can't catch it. A hard lock is
simple and makes the bug impossible. A warning would be clicked through,
and the result (doubled totals) is silent and hard to undo.

**Rejected alternatives.**
- *Warn before importing:* users click "continue"; the damage is silent.
- *Cross-format matching (FITID row ↔ content row):* fuzzy, and a wrong match loses real transactions.
- *One hash rule for both formats (always Rule B):* throws away FITID, the most reliable key for OFX.

---

## D-20 · Backups ping an external heartbeat; alert after 48 h without one
*2026-11-06 · security fix 5 · SPEC 4, 11.4, M9*

**Decision.** The nightly backup workflow's last step, which runs only after a
successful upload, pings a Healthchecks.io check (period 1 day, grace 1
day). If 48 hours pass without a ping, Healthchecks.io emails Jonathan. The
ping URL is the repo secret `HEALTHCHECK_BACKUP_URL`.

**Reason.** GitHub's docs say that in a public repository, scheduled workflows
are automatically disabled after 60 days without repository activity, and
this repo is public. Backups would then stop with nothing visibly broken. A
"dead man's switch" alerts on the *absence* of a success signal, so one
alert covers every failure: workflow disabled, dump error, R2 outage,
expired secret. It must live outside GitHub, because a GitHub-scheduled
checker would be disabled by the same rule. Healthchecks.io's free Hobbyist
plan (20 checks) is enough.

**Rejected alternatives.**
- *A second GitHub scheduled workflow that checks for recent backups:* disabled by the same 60-day rule.
- *A keep-alive action that makes empty commits:* noisy history, and it only covers the inactivity cause, not a failing dump.
- *The API checks backup age on `/health`:* the free Render instance sleeps, so nobody would be calling it.

---

## D-21 · Correct D-07: which models reject forced `tool_choice`
*2026-11-06 · security fix 6 · SPEC 7.2, 7.5*

**Decision.** D-07's wording "current Claude models reject `tool_choice`
`any`/`tool`" was too broad. It is corrected as follows:

- The restriction is **model-specific, not caused by thinking.** Claude Opus 5.5, Claude Sonnet 5.5, Claude Fable 5.1 and Claude Mythos 5.1 reject `any` and `tool` with a 400 regardless of thinking settings.
- Separately, on **any** model, manual extended thinking (`thinking: {type: "enabled"}`) blocks forced tool use.
- Claude Haiku 5.5, our `AI_MODEL_FAST`, **accepts** forced tool use (with thinking on, a forced call skips thinking).

For SEWE: the chat model (Sonnet 5.5) keeps `tool_choice: auto` +
`strict: true` + a prompt instruction + a check-and-retry when no tool was
called. Categorization doesn't need tools: it uses structured outputs
(`output_config.format`), which works on every model and removes most
invalid-JSON retries.

**Sources (official Anthropic docs, fetched 2026-11-06):**

- Define tools → "Forcing tool use", <https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools>:
  > "Not every model and setting supports forced tool use. Where it isn't supported, `tool_choice: {"type": "any"}` and `tool_choice: {"type": "tool", "name": "..."}` fail, whereas `tool_choice: {"type": "auto"}` (the default) and `tool_choice: {"type": "none"}` still work"

  Its table, row 1: "Manual extended thinking (`thinking: {type: "enabled"}`) — `any` and `tool` are not supported and result in an error … Adaptive thinking itself doesn't block forced tool use (models with thinking on by default, such as Claude Opus 5 and Claude Haiku 5.5, accept it, but a forced call skips thinking …); the models in the next row reject forced tool use regardless of thinking settings"

  Row 2: "Claude Opus 5.5, Claude Sonnet 5.5, Claude Fable 5.1, and Claude Mythos 5.1 — `any` and `tool` return a 400 error"
- Claude Sonnet 5.5 migration guide → "Forced tool use is not supported", <https://platform.claude.com/docs/en/models/sonnet-5-5/migration-guide>:
  > "Every earlier model on this page accepts a `tool_choice` of type `any` or `tool`. Claude Sonnet 5.5 rejects both with a 400 error, including on the token counting endpoint: `tool_choice: type "tool" and "any" are not supported for this model.`"

**Reason.** The original claim would have been wrong for Haiku 5.5. If someone
later sets `AI_MODEL_SMART` to a model that does accept forced tool use,
`auto` + check-and-retry still works, so the chat design doesn't depend on
which model is configured.

**Rejected alternatives.** *Keep D-07's wording:* it states a false general rule.

---

## D-22 · Cut V1 to ship faster; move the cut items to V1.1
*2026-11-06 · Jonathan's cut list · SPEC 2, 5, 6.2, 7, 8, 9, 13*

**Decision.** Moved to V1.1 (SPEC 13): native passkeys, EAS builds, app
stores, voice input, PDF import, gamification (XP, streaks, badges), and the
3-device cap with its `device_management` flow. V1 keeps the web deploy
(M9) and replaces the device cap with an **active-sessions list with
Revoke**. Removed from the schema: `devices`, `xp_events`, `sessions.scope`.

**Reason.** Jonathan's goal is to ship as fast as possible. Every cut item is
either native-only (V1 ships to the web), optional (voice, PDF), or
engagement polish (gamification). The device cap's lock-out risk needed a
whole recovery flow. A sessions list with Revoke gives the same visibility
and control for a fraction of the code. Nothing designed is lost: SPEC 13
keeps the notes, and D-05, D-06 and D-10 still describe how to build them.

**Rejected alternatives.** *Keep everything and work longer weeks:* not the goal.

---

## D-23 · Re-estimate after the cuts: ≈ 118 h ≈ 6 weeks
*2026-11-06 · SPEC 10*

**Decision.** Build 85 h + learning 13 h + 20% buffer = **≈ 118 h ≈ 6 weeks at
20 h/week** (range 5–7). It was 162 h ≈ 8 weeks in v1.1.

**Reason.** Cut from build time: native passkeys and EAS (≈ 7 h in M9), the
device-cap flow (≈ 3 h in M2), voice (≈ 2 h), PDF import (≈ 3 h), gamification
(≈ 4 h). Added: the Origin middleware, cookie test, `sid` revocation, format
lock and heartbeat (≈ 4 h in total). Learning time roughly halves with the
shorter teaching format (D-24). The buffer drops from 25% to 20% because the
riskiest outside-system work (store accounts, native builds) is gone.

**Rejected alternatives.** *Keep the 25% buffer:* there is less outside-system risk left to cover.

---

## D-24 · Shorter teaching: one-screen LEARN.md section + one exercise
*2026-11-06 · SPEC 1, 4, 10, 12*

**Decision.** Each milestone adds a LEARN.md section of about one screen (what
was built, one line per key file, up to 3 new concepts, commands, one "try
it") and one rewrite exercise with a ≤ 20-line README. `docs/explain/` is
dropped. CI also runs each exercise's reference solution against its tests.
M8's exercise becomes `build_export_bundle` because gamification (the old
`compute_progress`) is cut.

**Reason.** The request was to keep the teaching but keep it short. One place
to read per milestone (LEARN.md) is quicker than two overlapping documents.
Running reference solutions in CI proves the exercise tests are correct, so
a failing test always means the rewrite needs work, never that the test is
broken.

**Rejected alternatives.** *Keep `explain/M<n>.md`:* overlaps LEARN.md and costs about 1–2 h per milestone.

---

## D-25 · Email through Resend, behind `services/email.py`
*2026-11-06 · Q6 · SPEC 3, 4, 6.2, 11.3, 11.5, M2, M9*

**Decision.** `services/email.py` defines an `EmailSender` interface
(`send(to, subject, text, html=None)`) with two implementations:
`ConsoleEmailSender` (local dev and tests; prints the message) and
`ResendEmailSender` (prod). `EMAIL_PROVIDER` picks one. Mail is sent from
`jonathansewe.com`, shared across projects. Resend free tier as given by
Jonathan: 3,000 emails/month, 100/day, 1 domain. Amazon SES can be added
later as a third implementation without touching callers.

**Reason.** An interface keeps vendor code in one file, so a switch to SES
is one new class plus one env var. The console sender means local
development and CI never need a real key and never send real email. 100
emails/day is plenty for verification codes at V1 scale, but the limit is
shared with Jonathan's other projects, so signup-code sending is
rate-limited (6.2). DNS work for `jonathansewe.com` (SPF/DKIM) happens in M9.

**Rejected alternatives.**
- *Call Resend directly from routers:* vendor lock-in spread across files.
- *SMTP via a personal mailbox:* poor deliverability, credentials in env.

---

## D-26 · P1 rules reworded honestly; legacy sample data is invented
*2026-11-06 · Q3, Q4 · SPEC 3, 7.2, M1, M4*

**Decision.** The spec no longer says built-in rules are "ported from P1". They
are written new in M4, seeded from P1's sample merchant → category pairs.
`transactions.csv` stays in `legacy/`, and `legacy/README.md` states that its
data is invented.

**Reason.** P1 summed a hand-filled `category` column and had no rules to
port. An honest spec avoids a builder hunting for code that doesn't exist.
Labelling the sample data as invented answers the obvious question from
anyone reading a public repo of a finance app.

**Rejected alternatives.** *Rewrite git history to remove the CSV:* unnecessary, since the data is invented.

---

## D-27 · Masking also covers PayPal, Apple Cash and "TRANSFER TO/FROM <name>"
*2026-11-06 · Q10 · SPEC 6.4, M4*

**Decision.** Added patterns: `PAYPAL *<name>` (with an allowlist of merchants,
for example `NETFLIX`, kept unmasked), `APPLE CASH SENT MONEY TO/RECEIVED FROM
<name>`, and generic `TRANSFER TO/FROM <name>` (skipped when what follows is
an account reference such as `SAVINGS ...1234`).

**Reason.** These are the next most common places a third party's name
appears in a US statement. PayPal is the tricky one because it carries both
people and merchants, so a small allowlist keeps merchant names that
categorization needs. Account-reference detection keeps "transfer to
savings" categorizable as a transfer.

**Rejected alternatives.** *Mask everything after `PAYPAL *`:* would hide merchants and hurt categorization.

---

## D-28 · Link the design canvas; the spec wins where they differ
*2026-11-06 · Q5 · SPEC 9*

**Decision.** SPEC 9 links the canvas (Final V1 artboard). Tokens missing from
the v1.1 table were added from the canvas: `field`, `fieldLine`,
`accentText`, `heroSub`, `heroTile`, `frame`, `frameLine`, `islandLine`,
`islandText`. Header and island sizes were also taken from it. Canvas
elements for features cut from V1 (level pill, streak/XP card, "+20 XP",
mic, PDF, "Trusted devices 1 of 3") are omitted. The canvas's
"Two-factor (SMS + email)" is relabelled "Authenticator app (TOTP)" to
match the real security model.

**Reason.** The canvas was drawn before the V1 cuts and before TOTP was chosen.
Building cut features because they appear in a mockup would undo D-22.

**Rejected alternatives.** *Edit the canvas instead:* not requested; the spec is the source of truth for the build.

---

## D-29 · Stay non-commercial on Vercel Hobby; live-model eval approved
*2026-11-06 · Q7, Q9 · SPEC 3, 10 (M7)*

**Decision.** SEWE Finance is not commercial for now, so Vercel Hobby is fine.
If that changes, budget Vercel Pro. The manual live-model eval in M7 (about
20 questions, under $1 at Sonnet 5.5 prices) is approved.

**Reason.** Hobby's terms allow personal non-commercial use only. The eval is
the only way to check that the real model, not a recording, quotes Reports
numbers correctly.

**Rejected alternatives.** *Vercel Pro now:* $20/month for no benefit yet.

---

## D-30 · Push rights and branch workflow
*2026-11-06 · Q8 · SPEC 1*

**Decision.** Work happens on branches with pull requests. This session *can*
push to `main` (it has push and admin permission, and `main` has no branch
protection), but it won't. Recommendation for Jonathan: turn on branch
protection for `main` (require a PR and green CI).

**Finding to confirm:** on 2026-11-06 GitHub's API still reported the repo as
`jonathansewe/expense-categorizer`, and `jonathansewe/sewe-finance` was not
found. The rename may not have been saved. The spec uses the intended
name, `sewe-finance`.

**Reason.** PRs give Jonathan a review gate at every milestone, and CI must be
green before merge. Branch protection makes that a rule instead of a habit.

**Rejected alternatives.** *Push straight to `main`:* no review gate, and CI runs only after the fact.

---

# M1 build decisions

## D-31 · M1 toolchain choices
*2026-11-06 · M1*

**Decision.**
- **Python deps with `uv`** (`pyproject.toml` + `uv.lock`), Python 3.12 pinned in `api/.python-version`.
- **API image installs uv from PyPI** (`pip install uv==<version>`) instead of copying it from `ghcr.io`.
- **Expo SDK 58**, Expo Router, **web output `single`** (one static `index.html` + JS bundle).
- **ESLint** with `eslint-config-expo`, warnings fail the build (`--max-warnings 0`).
- **Jest projects:** `app` (component and unit tests) and `exercises` (`SOLUTION=reference` in CI).
- **Theme and language saved on the device** with AsyncStorage until accounts exist (M2 moves them to `user_settings`).
- **A device that reports no color scheme gets light** (`resolveTheme`).

**Reason.** uv gives a lock file and fast, reproducible installs with one tool.
Installing uv from PyPI works through more networks and proxies than
ghcr.io (this build environment blocks ghcr.io). `single` output is the
simplest thing to host on Vercel (one rewrite to `index.html`) and avoids
pre-render/hydration mismatches with device-local preferences. Failing on
warnings keeps the lint output at zero, so new warnings get noticed.
Light is the browser default when no preference is reported.

**Rejected alternatives.**
- *pip + requirements.txt:* no lock file of the whole dependency tree by default.
- *Web output `static` (pre-rendered pages):* each page would first render with default preferences, then flash to the saved theme.
- *Fonts from the system only:* doesn't match the design (Space Grotesk headings).

## D-32 · Template files removed from the Expo scaffold
*2026-11-06 · M1*

**Decision.** Removed what `create-expo-app` generated beyond the app itself:
`AGENTS.md` (AI-assistant notes saying routes live in `src/app/`, which
contradicts SPEC 4), `.claude/settings.json` (it enabled a third-party
assistant plugin), and Expo's template `LICENSE`.

**Reason.** The repo's layout is set by the spec, assistant configuration is
Jonathan's call, and a license should be chosen on purpose rather than
inherited from a template.

**Rejected alternatives.** *Keep them:* conflicting instructions in the repo.

---

# M2 build decisions

D-33 to D-43 were agreed with Jonathan before coding (2026-11-11). D-44 to
D-54 are judgment calls made while building M2.

## D-33 · No session links in commits or pull requests
*2026-11-11 · M2*

**Decision.** The first M2 commit adds `.claude/settings.json` with
`{"attribution": {"sessionUrl": false}}`. Commits end with only the
`Co-Authored-By` trailer; PR bodies with only the "Generated with Claude
Code" line. No claude.ai session links anywhere.

**Reason.** Jonathan's call: session links are private working history, and
the repo is public. This file is unrelated to the scaffold's
`app/.claude/settings.json` removed in D-32 (that one enabled a third-party
plugin).

**Rejected alternative.** *Rely on remembering:* a setting can't forget.

## D-34 · Refresh rotation with a 20-second grace period
*2026-11-11 · SPEC 6.2 item 5 · `security/sessions.py`*

**Decision.** The next refresh secret is derived, not random:
`next = HMAC(key, session_id ‖ current_secret)`. If the immediately previous
secret is presented within 20 s of its rotation, the API answers with the
**same** next refresh token (and a fresh access token) and revokes nothing.
Rotation is a conditional `UPDATE … WHERE refresh_token_hash = :old`, so two
simultaneous rotations can't fork the chain; the loser falls into the grace
path.

**Reason.** On the web the refresh cookie is shared by every tab. Two tabs
reloading together both send the same cookie; serializing inside one tab's
JavaScript can't stop that. Without grace, the second request looks like
token reuse and logs the user out. Deriving the next secret means the server
can hand out the same token again without ever storing a secret in plain
text. 20 s covers slow networks; anything later is treated as reuse.

**Rejected alternatives.**
- *Revoke on any reuse (strict rotation):* random logouts with two tabs open.
- *Store the next secret encrypted for 20 s:* more state, and a readable secret at rest.
- *No rotation:* a stolen refresh token would work for 30 days.

## D-35 · Reuse detection only for secrets we really issued
*2026-11-11 · SPEC 6.2 item 5*

**Decision.** Each rotation writes the old secret's hash to
`refresh_token_history`. A presented secret that matches a history row
(outside the grace window) revokes the session: 401 `refresh_reused`. A
secret that matches nothing: 401 `refresh_invalid`, and the session lives on.

**Reason.** Reuse of a real, rotated-out token means two parties hold it:
one of them is a thief, so killing the session is right. A secret we never
issued proves nothing except that someone knows a session id; revoking for
that would let anyone log a user out.

**Rejected alternative.** *Revoke on any mismatch (the first draft):* a cheap logout attack.

## D-36 · Client IP only from a trusted proxy
*2026-11-11 · SPEC 6.2 item 7 · `security/rate_limit.py`, `Dockerfile`, `config.py`*

**Decision.** uvicorn runs with `--proxy-headers`; it trusts
`X-Forwarded-For` only from peers in `FORWARDED_ALLOW_IPS` and then takes
the right-most untrusted entry. The rate limiter reads only
`request.client.host`, never the header. In production the API **refuses to
start** if `FORWARDED_ALLOW_IPS` is still `127.0.0.1` (or uvicorn's
`127.0.0.1,::1`, or empty), and also if it is `*`.

**Reason.** Any client can write `X-Forwarded-For`, so reading it directly
lets an attacker pick a new IP per request and dodge the per-IP limit.
Behind Render's proxy with `127.0.0.1`, every request would come from the
proxy's IP, and one shared per-IP limit would lock out all users together
(Jonathan's addition). With `*`, every hop is trusted, so uvicorn would take
the left-most entry: the one the client wrote.

**Open for M9.** The right value on Render depends on how its proxy reaches
the container and builds `X-Forwarded-For`; check Render's docs then. The
per-account limit doesn't depend on the IP, so password guessing stays capped.

**Rejected alternative.** *Warn instead of refusing to start:* a log line is easy to miss; a failed deploy isn't.

## D-37 · Constant-time comparisons for every secret
*2026-11-11 · `security/hashing.py`*

**Decision.** `hmac.compare_digest` for TOTP codes, email-code hashes,
recovery-code hashes and refresh-secret hashes. Recovery codes: load the
user's unused hashes and compare against each, so a hash is never used as a
SQL lookup key. TOTP checks all steps in the window even after a match.

**Reason.** `==` stops at the first different byte, and response time can
leak how much of a guess was right.

## D-38 · Login doesn't reveal which emails have accounts
*2026-11-11 · `routers/auth.py`*

**Decision.** An unknown email still runs argon2 against a fixed dummy hash.
`email_not_verified` is returned only after the password is verified; a
wrong password on an unverified account gets `invalid_credentials`, like any
other wrong password.

**Reason.** Skipping argon2 for unknown emails makes them answer ~50 ms
faster: a timing oracle for "does this person use SEWE?". Saying "not
verified" before checking the password would be a direct oracle.

## D-39 · JWT algorithm pinned, purposes kept apart
*2026-11-11 · `security/tokens.py`*

**Decision.** Decoding allows only HS256 and requires `exp`, `iat`, `sub`
and `purpose` (plus `sid` for access tokens). `purpose` is `access` or
`mfa`; each endpoint accepts exactly one.

**Reason.** Trusting the token's own `alg` header allows `none` and
algorithm-confusion attacks. Without `purpose`, the 5-minute MFA token
(issued after only the password) would work as an access token and skip TOTP.

## D-40 · Passkeys require user verification
*2026-11-11 · `routers/passkeys.py`*

**Decision.** `userVerification: "required"` in registration and
authentication options, and `require_user_verification=True` in both
verify calls. Registration also requires a discoverable credential, so
sign-in needs no email first.

**Reason.** A passkey sign-in replaces password + TOTP, so it must prove
two factors: the device (something you have) unlocked by biometrics or PIN
(something you are or know). Without UV, a stolen unlocked security key
alone would be enough.

## D-41 · Single-use by conditional UPDATE
*2026-11-11*

**Decision.** TOTP replay guard:
`UPDATE users SET totp_last_used_step = :step WHERE id = :id AND
(totp_last_used_step IS NULL OR totp_last_used_step < :step)`; 0 rows →
reject. The same pattern consumes recovery codes (`WHERE used_at IS NULL`),
counts email-code attempts (`WHERE attempts < 5`), uses passkey challenges
and rotates refresh tokens.

**Reason.** "Read, check, then write" lets two simultaneous requests both
pass the check. A conditional UPDATE makes the database decide: only one
can change the row. A test fires two requests with one TOTP code at once.

## D-42 · Email codes stored as keyed hashes
*2026-11-11 · `security/codes.py`, `security/hashing.py`*

**Decision.** `code_hash = HMAC-SHA256(key, user_id ‖ code)`, with the key
derived by HKDF from `DATA_ENCRYPTION_KEY` (one sub-key per purpose).

**Reason.** There are only 1,000,000 six-digit codes, so a plain SHA-256
from a leaked database is reversed in milliseconds. A keyed hash can't be
brute-forced without the server key.

**Rejected alternative.** *argon2 for codes:* slow on purpose, which a 10-minute code doesn't need once it's keyed.

## D-43 · Refresh cookie attributes, tested on every flow
*2026-11-11 · SPEC 6.1 · `security/cookies.py`, `tests/test_cookies.py`*

**Decision.** `refresh_token`: `HttpOnly; Secure; SameSite=Strict;
Path=/api/v1/auth/refresh`, never `Domain` (confirmed by Jonathan:
`/api/v1/auth/refresh`, as SPEC 6.1 and D-18 say). The test checks every
attribute on every Set-Cookie from verify-email, login, totp/verify,
recovery/verify, passkey login, refresh (success and failure), logout and
self-revoke.

**SameSite check.** Production app and API share `jonathansewe.com`, so
they are same-site and `Strict` works. Local `localhost:8081` ↔
`localhost:8000` is same-site too. Vercel previews are cross-site but go
through the `/api` rewrite (same origin). No problem found.

## D-44 · Login with TOTP returns an MFA token first
*2026-11-11 · SPEC 6.2, 8*

**Decision.** Password OK and TOTP on → `{"mfa_required": true,
"mfa_token": ...}` (5-minute JWT, `purpose=mfa`); `/auth/totp/verify` or
`/auth/recovery/verify` with that token then starts the session. Without
TOTP, the session starts at once, but `require_totp` blocks bank-data
routes. `/auth/totp/verify` without `mfa_token` (and with a Bearer token)
confirms setup instead. The app keeps the MFA token in memory, never in the
URL.

**Reason.** The spec's endpoint list has one `totp/verify`; these are its
two natural jobs. No half-signed-in session row exists before the second
factor.

## D-45 · Repeat signups resend the code; answers never differ
*2026-11-11 · `routers/auth.py`*

**Decision.** `/signup` always answers 202 `verification_sent`. For a new or
unverified email it (re)sends a code and replaces the password; for a
verified email it does nothing. There is no separate "resend" endpoint.
Codes per email are capped at 3 per hour (Resend's free tier is shared).

**Reason.** Different answers would reveal registered emails. Replacing the
password of an unverified account stops a stranger from pre-registering
someone else's email: whoever reads the inbox decides. Known limit: an
expired code answers `code_expired`, which shows a signup is pending.

## D-46 · A verified email signs you in
*2026-11-11*

**Decision.** A correct `/verify-email` code starts a session, so the user
goes straight to TOTP setup without typing the password again.

**Reason.** The code proves inbox access, and the password was set seconds
ago in the same flow.

## D-47 · Schema and endpoints added beyond SPEC 5 and 8
*2026-11-11*

| Addition | Why |
|---|---|
| `users.totp_enabled_at` | TOTP is "on" only after a code confirms setup |
| `users.totp_last_used_step` | Replay guard (D-41) |
| `refresh_token_history` | Reuse detection (D-35) |
| `sessions.rotated_at` | Grace window (D-34) |
| `email_verification_codes` | 10-minute codes, 5 tries, hashed (D-42) |
| `webauthn_challenges` | One-time passkey challenges |
| `GET /me` | The app must know after a reload whether TOTP is on and a passkey exists |
| `GET/PATCH /settings` (theme, language) | SPEC 9: saved to `user_settings` from M2 |

## D-48 · Recovery codes: 10 × 60 bits, keyed hashes
*2026-11-11 · `security/codes.py`*

**Decision.** 12 characters from Crockford base32 (no i, l, o, u),
shown as `xxxx-xxxx-xxxx`; input ignores case, spaces and dashes. Stored as
HMAC-SHA256 bound to the user id. Regenerating needs a current TOTP code.

**Reason.** 60 random bits plus rate limits make guessing hopeless, so a
fast keyed hash is enough; argon2 × 10 per attempt would be slow for no
gain. A TOTP code for regeneration means a stolen access token alone can't
mint new codes.

## D-49 · In-memory rate limiter
*2026-11-11 · `security/rate_limit.py`*

**Decision.** A sliding window in the API process: 5 per minute per IP and
per account on login, verify-email, TOTP, recovery and passkey sign-in;
429 `rate_limited` with `Retry-After`.

**Reason.** One Render instance runs one process, so in-memory counters are
correct and need no Redis. Known limit: they reset on restart and aren't
shared between workers. Move them to Postgres or Redis before scaling out.

## D-50 · Log events, never secrets or addresses
*2026-11-11 · SPEC 6.3*

**Decision.** Auth code logs event names only (`login.failed`,
`refresh.failed`, `origin.rejected`...): no emails, codes, tokens or header
values. Validation errors name the bad fields but never echo values. The
one exception is the console email sender, which prints emails (and their
codes) because that is its whole purpose in local development; production
uses Resend.

## D-51 · Browsers get the refresh token as a cookie, native apps in the body
*2026-11-11 · SPEC 6.1 · `security/cookies.py`*

**Decision.** The API decides by the `Origin` header: present (a browser)
→ HttpOnly cookie, and the JSON body has `refresh_token: null`; absent (the
native app) → the token is in the body, and no cookie is set.

**Reason.** Browsers always send `Origin` on POST, and the native app never
does; the Origin middleware (D-16) already relies on that split. Putting the
refresh token in a browser-readable body would undo HttpOnly.

**Spec reading.** SPEC 6.1 says a missing Origin is allowed only for
requests that "authenticate with a Bearer header or a refresh token in the
body". Native signup and login have neither yet, so the middleware checks
only "no cookies", and each endpoint enforces its own authentication.

## D-52 · `credentials: 'include'` on every /auth/* call
*2026-11-11 · `app/lib/api.ts` · correction to the M2 plan*

**Decision.** The app sends `credentials: 'include'` on every `/auth/*`
request, not only on `/auth/refresh`.

**Reason.** The plan said "only on refresh", but the web app (`:8081`) and
the API (`:8000`) are different origins, and a browser **ignores**
`Set-Cookie` on a cross-origin fetch unless the request asked for
credentials. Login, verify-email, totp/verify, recovery/verify and passkey
login all set the cookie; logout clears it. The cookie's own
`Path=/api/v1/auth/refresh` still keeps it from being *sent* anywhere else.

## D-53 · Passkeys are the default sign-in once a browser has used one
*2026-11-11 · SPEC 6.2 item 3*

**Decision.** After the first sign-in on a WebAuthn-capable browser, the
app offers a passkey once ("Not now" is remembered on the device). After
this browser registers or uses a passkey, the sign-in screen shows
"Sign in with a passkey" as the primary button.

**Reason.** The API can't say whether an email has a passkey before
sign-in without leaking that the account exists, so "default" is decided
per browser.

## D-54 · TOTP setup comes before the tabs
*2026-11-11 · SPEC 6.2 item 2*

**Decision.** A signed-in user without TOTP is sent to the setup screen
before seeing the tabs; the API also enforces it with `require_totp`, which
M3's import routes will use.

**Reason.** Every V1 feature needs imported bank data, and bank data needs
TOTP (SPEC 6.2), so the app would be empty without it. Sending the user to
setup at once is clearer than letting them find out at the import screen.

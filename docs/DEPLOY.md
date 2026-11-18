# Deploying SEWE Finance

How production is wired, and the steps that can only be done by hand in each
provider's dashboard. Why it's set up this way: D-55 (and D-02, D-03, D-15,
D-25, D-29, D-36) in `docs/DECISIONS.md`.

## What runs where

| Piece | Host | Address | Defined in |
|---|---|---|---|
| Web app (static Expo web export) | Vercel, Hobby | `https://finance.jonathansewe.com` | `app/vercel.json` + Vercel dashboard |
| API (FastAPI, Docker) | Render web service `sewe-finance-api`, free, Virginia | `https://api.finance.jonathansewe.com` | `render.yaml` + Render dashboard |
| Database | Neon Postgres 16, Free, AWS us-east-1 | private connection string | Neon dashboard |
| Email | Resend, domain `jonathansewe.com` | from `finance@jonathansewe.com` | Resend dashboard |
| DNS | Cloudflare, zone `jonathansewe.com` | — | Cloudflare dashboard |

Deploys after setup:
- **API:** a push to `main` that touches `api/**` deploys **after CI passes** (`autoDeployTrigger: checksPass`). The container runs `alembic upgrade head` before starting, so migrations go out with the code.
- **Web:** Vercel builds every push to `main` (production) and every other branch (preview URL).

## Environment variables

### API (Render)

With `APP_ENV=prod` the API **refuses to start** if any value marked ✔ in the
last column is still a development default (`api/app/config.py`). A failed
deploy log saying `Unsafe production settings: ...` names the problem.

| Variable | Value | Set by | Checked |
|---|---|---|---|
| `APP_ENV` | `prod` | `render.yaml` | |
| `PORT` | `8000` (the port the Dockerfile serves on) | `render.yaml` | |
| `DATABASE_URL` | Neon **direct** URL, scheme changed to `postgresql+psycopg://`, ending `?sslmode=require` | dashboard (step 4) | |
| `JWT_SECRET` | random, made by Render | `render.yaml` (`generateValue`) | ✔ |
| `DATA_ENCRYPTION_KEY` | 32 random bytes, base64 (command in step 4) | dashboard (step 4) | ✔ |
| `RESEND_API_KEY` | from Resend (step 2) | dashboard (step 4) | ✔ |
| `EMAIL_PROVIDER` | `resend` | `render.yaml` | ✔ |
| `EMAIL_FROM` | `SEWE Finance <finance@jonathansewe.com>` | `render.yaml` | |
| `ALLOWED_ORIGINS` | `https://finance.jonathansewe.com` | `render.yaml` | |
| `WEBAUTHN_RP_ID` | `finance.jonathansewe.com` | `render.yaml` | |
| `WEBAUTHN_ORIGIN` | `https://finance.jonathansewe.com` | `render.yaml` | |
| `COOKIE_SECURE` | `true` | `render.yaml` | ✔ |
| `FORWARDED_ALLOW_IPS` | `10.0.0.0/8` (provisional, tested in steps 10-11) | `render.yaml` | ✔ |

Variables for later milestones (`ANTHROPIC_API_KEY`, `AI_MODEL_*`, `R2_*`)
are listed in SPEC 11.3 and get added here when their milestone ships.

### Web (Vercel)

| Variable | Value | Scope |
|---|---|---|
| `EXPO_PUBLIC_API_URL` | `https://api.finance.jonathansewe.com/api/v1` | Production |

It is baked into the JavaScript at **build** time, so after changing it you must
redeploy for it to take effect. It's public by design (it's in the bundle); never
put a secret in an `EXPO_PUBLIC_` variable.

## Checklist: what you do by hand

Do these in order: each step uses something the previous one created.

**1. Neon: create the database**
1. Sign up at neon.com (GitHub login is fine). Create a project `sewe-finance`, Postgres **16** (same as local and CI), region **AWS US East 1 (N. Virginia)**, database name `sewe`.
2. Dashboard → **Connect**. Turn **Connection pooling off** to get the *direct* URL (its host has no `-pooler`). Alembic and psycopg's prepared statements don't work through the pooler's transaction mode, and one API instance doesn't need pooling.
3. Change the scheme: `postgresql://...` → `postgresql+psycopg://...`. Keep `?sslmode=require` at the end. Keep it somewhere safe for step 4.
4. Settings → turn on usage email alerts.

**2. Resend: domain and API key**
1. Sign up at resend.com. **Domains → Add domain** → `jonathansewe.com` (region us-east-1).
2. Leave the page open: it lists the DNS records for step 3 (an MX and a TXT on `send`, a DKIM TXT on `resend._domainkey`).
3. **API Keys → Create**: name `sewe-finance-prod`, permission **Sending access**, domain `jonathansewe.com`. Copy it now (it's shown once).

**3. Cloudflare: email records**
1. Cloudflare → `jonathansewe.com` → **DNS → Records**. Add each record Resend shows, copying name, type, value and priority exactly. Proxy status doesn't apply to MX/TXT.
2. These live on `send.` and `resend._domainkey.`, so they **don't touch** the root SPF/MX of the resume site or any other mail you have.
3. Look for an existing `_dmarc` TXT. If there is one, leave it alone. If there isn't, add TXT `_dmarc` = `v=DMARC1; p=none;` (monitor-only; never two DMARC records).
4. Back in Resend, click **Verify DNS records**. It may take minutes; finish the next steps meanwhile.

**4. Render: the API**
1. Sign up at render.com with GitHub and give it access to `jonathansewe/sewe-finance` only.
2. **New → Blueprint** → choose the repo, branch `main`. Render reads `render.yaml` and asks for the three `sync: false` values:
   - `DATABASE_URL`: the URL from step 1.3.
   - `DATA_ENCRYPTION_KEY`: run locally
     `python -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())"`.
     **Save it in your password manager first.** Without it, every encrypted field in the database is unreadable forever.
   - `RESEND_API_KEY`: the key from step 2.3.
3. Apply. Watch **Logs**: migrations run, then uvicorn starts. Open `https://sewe-finance-api.onrender.com/api/v1/health` (or the URL Render shows) and confirm `{"status":"ok","database":"ok"}`.
4. Service → **Settings → Custom Domains → Add** → `api.finance.jonathansewe.com`. Render shows a CNAME target (`sewe-finance-api.onrender.com`).

**5. Cloudflare: API record**
1. Add **CNAME** `api.finance` → `sewe-finance-api.onrender.com` (use Render's exact target). Proxy status **DNS only (grey cloud)**. Two reasons: Cloudflare's free certificate covers `*.jonathansewe.com` but not two levels down (`api.finance.`), so a proxied record would fail TLS; and an extra proxy would change which IP the API sees (step 10).
2. In Render, click **Verify** next to the domain. Wait for the certificate (✓ Certificate issued).
3. Check `https://api.finance.jonathansewe.com/api/v1/health`.

**6. Vercel: the web app**
1. Sign up at vercel.com with GitHub (Hobby plan; non-commercial, D-29). **Add New → Project** → import `jonathansewe/sewe-finance`.
2. **Root Directory: `app`**. Framework Preset: **Other**. Leave the build settings alone (`app/vercel.json` sets them).
3. **Environment Variables:** `EXPO_PUBLIC_API_URL` = `https://api.finance.jonathansewe.com/api/v1`, environment **Production** only.
4. Deploy. Then **Settings → Domains → Add** → `finance.jonathansewe.com`. Vercel shows the record it wants.

**7. Cloudflare: web record**
1. Add **CNAME** `finance` → the target Vercel shows (usually `cname.vercel-dns.com`), **DNS only (grey cloud)**. Vercel issues its own certificate and needs to see the request directly.
2. If Vercel asks for a TXT `_vercel` record (domain ownership), add it as shown.
3. Wait until Vercel shows the domain as **Valid Configuration**.

**8. Resend: confirm verified**
Resend → Domains → `jonathansewe.com` must say **Verified**. Until then the API can't send signup codes.

**9. Smoke test (browser: Chrome or Firefox)**
1. Open `https://finance.jonathansewe.com`, sign up, receive the code email, verify.
2. Set up TOTP, save the recovery codes, register a passkey.
3. Reload the page: you should stay signed in (the refresh cookie works).
4. DevTools → Application → Cookies → `https://api.finance.jonathansewe.com`: `refresh_token` has **no Domain** (host-only), `Path=/api/v1/auth/refresh`, `HttpOnly`, `Secure`, `SameSite=Strict`.
5. Log out, then sign in with the passkey.
6. Gmail → the code email → "Show original": SPF, DKIM and DMARC all **PASS**.

**10. Per-IP limit sees real client IPs (D-36)**
The limiter counts 5 tries per minute per IP **and** per account, so this test
uses a different made-up email each time; that way only the IP limit can trigger.
1. On your phone, **on mobile data (Wi-Fi off)**, try to sign in 6 times with made-up emails (`test1@example.com`, `test2@example.com`, ...) and any password. The 6th answer is "too many attempts".
2. Within that minute, on your laptop (Wi-Fi), sign in to your real account. It **must work**. If it's also blocked, the API sees one shared proxy IP for everybody: stop and tell Claude (Q18).

**11. The client can't fake its IP (D-36)**
Run from your laptop in Git Bash. Each request claims a different fake IP and
uses a different email (no `Origin` header, so the Origin check lets it through
as a native-style request):
```
for i in 1 2 3 4 5 6; do curl -s -o /dev/null -w "%{http_code}\n" -X POST https://api.finance.jonathansewe.com/api/v1/auth/login -H "Content-Type: application/json" -H "X-Forwarded-For: 203.0.113.$i" -d "{\"email\":\"spoof$i@example.com\",\"password\":\"wrong-password\"}"; done
```
The last line must be **429**. If none is 429, the API believes the fake header: stop and tell Claude (Q18).

**12. Housekeeping**
1. GitHub → Settings → Branches: protect `main` (require a PR and the 4 CI checks). D-30.
2. Render deploys only when checks pass, so a red CI on `main` means no deploy. That's intended.
3. Vercel previews (`*.vercel.app`) can show the UI but **can't sign in**: the prod API's Origin check rejects them. Intended (SPEC 6.1).

## Not done yet (still in M9)

- **Backups (D-03, D-20).** Neon Free has only a short restore window. Until `backup.yml` exists, don't keep data you can't re-import.
- Privacy policy page, README screenshots, a Content-Security-Policy header.
- **Cold starts:** the free Render service sleeps after 15 minutes idle; the first request then takes about a minute. Starter ($7/month) removes this (Q17).

## When something breaks

| Symptom | Likely cause |
|---|---|
| Render deploy fails with `Unsafe production settings: ...` | A ✔ variable above is missing or still a dev value; the message names it. |
| Health check returns 503 | `DATABASE_URL` wrong, or missing `+psycopg` / `sslmode=require`. |
| Web loads but every call fails with a CORS error | `EXPO_PUBLIC_API_URL` missing (the build used `localhost`), or not redeployed after setting it. |
| Signed out on every reload | Cookie blocked: check that both hosts are on `jonathansewe.com` and the DNS records are grey-cloud. |
| 403 `origin_not_allowed` | Page isn't `https://finance.jonathansewe.com` (e.g. a preview URL). |
| Signup says email failed | Resend domain not verified yet (step 8), or wrong `RESEND_API_KEY`. |

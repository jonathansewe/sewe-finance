# SEWE Finance

A personal-finance app that reads your bank statements, sorts every
transaction with rules and AI, and answers questions about your money.
Read-only: it never moves money.

**Status:** milestone M1 (skeleton) of 9. See [`docs/SPEC.md`](docs/SPEC.md) for
the full plan and [`LEARN.md`](LEARN.md) for a plain-English tour of the code.

```
Expo app (web, iOS, Android) ──HTTPS──▶ FastAPI ──▶ PostgreSQL
finance.jonathansewe.com                 api.finance.jonathansewe.com
```

| Folder | What's inside |
|---|---|
| `app/` | Expo (React Native) app in TypeScript |
| `api/` | FastAPI backend in Python 3.12 |
| `docs/` | Spec, decision log, open questions |
| `exercises/` | One rewrite-it-yourself exercise per milestone |
| `legacy/` | P1, the original expense-categorizer script |

## Run it locally

You need Docker, Node 22 and [uv](https://docs.astral.sh/uv/).

API + database:

```bash
docker compose up --build
```

Check it: <http://localhost:8000/api/v1/health> should answer `{"status":"ok","database":"ok"}`.

Web app (second terminal):

```bash
cd app && npm install && npm run web
```

Open <http://localhost:8081>.

## Tests

API (needs the database from `docker compose up`):

```bash
cd api && uv sync && uv run pytest
```

App:

```bash
cd app && npm test
```

CI runs both, plus lint and type checks, on every push (`.github/workflows/ci.yml`).

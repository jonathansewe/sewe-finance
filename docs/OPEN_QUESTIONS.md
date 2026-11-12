# Open questions for Jonathan

## Answered (2026-11-06)

All twelve v1.1 questions are answered and recorded as decisions:
Q1 → D-15, Q2 → D-02 (kept), Q3/Q4 → D-26, Q5 → D-28, Q6 → D-25,
Q7/Q9 → D-29, Q8 → D-30, Q10 → D-27, Q11 → D-22/D-23, Q12 → D-24.

## Answered (2026-11-11, start of M2)

| # | Question | Answer |
|---|---|---|
| Q14 | Turn on branch protection for `main`? | Yes: `main` requires a pull request and 4 passing CI checks. The CI job names are now load-bearing; don't rename them. |
| Q16 | Resend sending address? | `finance@jonathansewe.com` in production (`EMAIL_FROM`); local and CI use the console sender. |

## Still open

| # | Question | Blocks | My recommendation |
|---|---|---|---|
| Q13 | **Did the repo rename save?** On 2026-11-06 GitHub's API still returned `jonathansewe/expense-categorizer`, and `jonathansewe/sewe-finance` was not found. | M9 (README links, deploy hooks) | Check Settings → General → Repository name. Everything still works under the old name in the meantime. |
| Q15 | **Healthchecks.io account for the backup alert** (D-20). | M9 | Create a free Hobbyist account with the email you read daily. |
| Q17 | **Render plan when someone else starts using it:** free (1-minute cold starts) or Starter ($7/month)? | M9 | Free while it's only you; Starter before you share the link. |
| Q18 | **`FORWARDED_ALLOW_IPS` on Render** (D-36). Production refuses `127.0.0.1` and `*`; the right value is the address range Render's proxy uses to reach the container. | M9 (the API won't start in prod without it) | I'll check Render's docs during M9 and test that the per-IP limit sees real client IPs before launch. |

# M2 exercise: `verify_totp`

Rewrite TOTP checking yourself in `my_verify_totp.py`, with only the standard library (`hmac`, `hashlib`, `struct`, `base64`). No pyotp, no AI help.

```python
verify_totp(secret: str, code: str, at_time: int) -> bool
```

- `secret` is base32 (what the QR code holds). Accept lowercase, spaces, and missing `=` padding. A secret that isn't base32 raises `ValueError`.
- `code` is 6 ASCII digits; spaces inside are ignored ("287 082"). Anything else → `False`.
- `at_time` is Unix seconds. The step is `at_time // 30`; HMAC-SHA1 the step as an 8-byte big-endian number, then apply RFC 4226 "dynamic truncation" and keep the last 6 digits.
- Accept the step before and after too (clock drift), never two steps away.
- Compare codes with `hmac.compare_digest`, not `==`.

Run your version (from `api/`):

```bash
uv run pytest ../exercises/M2
```

Hint: the test vectors are RFC 6238 Appendix B. The reference is `api/app/security/totp.py`; don't open it until your tests pass.

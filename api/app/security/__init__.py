"""Security building blocks: passwords, tokens, hashing, encryption, TOTP, codes.

Each module does one job and has no FastAPI routes. Routers combine them.
Keeping the crypto here means there is exactly one place to review it.
"""

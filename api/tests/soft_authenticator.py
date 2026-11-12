"""A tiny software passkey authenticator for tests.

It does what a phone or security key does, minus the hardware: makes a
P-256 key pair, builds the WebAuthn registration and assertion responses,
and signs them. `user_verified=False` clears the UV flag, which is how the
tests prove the API requires user verification (D-40).
"""

import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from webauthn.helpers import bytes_to_base64url
from webauthn.helpers.encode_cbor import encode_cbor

FLAG_UP, FLAG_UV, FLAG_AT = 0x01, 0x04, 0x40


@dataclass
class SoftAuthenticator:
    rp_id: str = "localhost"
    origin: str = "http://localhost:8081"
    credential_id: bytes = field(default_factory=lambda: os.urandom(16))
    key: ec.EllipticCurvePrivateKey = field(
        default_factory=lambda: ec.generate_private_key(ec.SECP256R1())
    )
    sign_count: int = 0
    user_handle: bytes = b""

    def _client_data(self, kind: str, challenge_b64: str, origin: str | None) -> bytes:
        return json.dumps(
            {
                "type": kind,
                "challenge": challenge_b64,
                "origin": origin or self.origin,
                "crossOrigin": False,
            }
        ).encode()

    def _cose_public_key(self) -> bytes:
        numbers = self.key.public_key().public_numbers()
        return encode_cbor(
            {
                1: 2,
                3: -7,
                -1: 1,
                -2: numbers.x.to_bytes(32, "big"),
                -3: numbers.y.to_bytes(32, "big"),
            }
        )

    def _flags(self, user_verified: bool, attested: bool = False) -> bytes:
        flags = FLAG_UP | (FLAG_UV if user_verified else 0) | (FLAG_AT if attested else 0)
        return bytes([flags])

    def register(
        self, options: dict[str, Any], user_verified: bool = True, origin: str | None = None
    ) -> dict[str, Any]:
        self.user_handle = _b64url_decode(options["user"]["id"])
        rp_hash = hashlib.sha256(self.rp_id.encode()).digest()
        attested = (
            bytes(16)  # AAGUID: all zeros for a "none" attestation
            + len(self.credential_id).to_bytes(2, "big")
            + self.credential_id
            + self._cose_public_key()
        )
        auth_data = (
            rp_hash + self._flags(user_verified, attested=True) + (0).to_bytes(4, "big") + attested
        )
        attestation = encode_cbor({"fmt": "none", "attStmt": {}, "authData": auth_data})
        client_data = self._client_data("webauthn.create", options["challenge"], origin)
        cred_id = bytes_to_base64url(self.credential_id)
        return {
            "id": cred_id,
            "rawId": cred_id,
            "type": "public-key",
            "response": {
                "clientDataJSON": bytes_to_base64url(client_data),
                "attestationObject": bytes_to_base64url(attestation),
                "transports": ["internal"],
            },
            "clientExtensionResults": {},
        }

    def login(
        self, options: dict[str, Any], user_verified: bool = True, origin: str | None = None
    ) -> dict[str, Any]:
        self.sign_count += 1
        rp_hash = hashlib.sha256(self.rp_id.encode()).digest()
        auth_data = rp_hash + self._flags(user_verified) + self.sign_count.to_bytes(4, "big")
        client_data = self._client_data("webauthn.get", options["challenge"], origin)
        signed = auth_data + hashlib.sha256(client_data).digest()
        signature = self.key.sign(signed, ec.ECDSA(hashes.SHA256()))
        cred_id = bytes_to_base64url(self.credential_id)
        return {
            "id": cred_id,
            "rawId": cred_id,
            "type": "public-key",
            "response": {
                "clientDataJSON": bytes_to_base64url(client_data),
                "authenticatorData": bytes_to_base64url(auth_data),
                "signature": bytes_to_base64url(signature),
                "userHandle": bytes_to_base64url(self.user_handle),
            },
            "clientExtensionResults": {},
        }


def _b64url_decode(value: str) -> bytes:
    import base64

    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

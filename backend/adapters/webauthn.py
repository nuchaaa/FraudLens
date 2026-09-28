"""WebAuthn protocol adapter. Private authenticator keys never enter FraudLens."""

import json
from typing import cast
from uuid import UUID

from webauthn import (
    base64url_to_bytes,
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers.exceptions import InvalidAuthenticationResponse, InvalidRegistrationResponse
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    UserVerificationRequirement,
)

from backend.app.identity.ports import (
    InvalidMfaResponse,
    MfaCredential,
    VerifiedMfaCredential,
)


class PyWebAuthnVerifier:
    def credential_id(self, response: dict[str, object]) -> bytes:
        value = response.get("id")
        if not isinstance(value, str) or len(value) > 1400:
            raise InvalidMfaResponse("invalid authenticator response")
        try:
            credential_id = base64url_to_bytes(value)
        except (ValueError, TypeError) as exc:
            raise InvalidMfaResponse("invalid authenticator response") from exc
        if not 1 <= len(credential_id) <= 1024:
            raise InvalidMfaResponse("invalid authenticator response")
        return credential_id

    def registration_options(
        self, *, rp_id: str, account_id: UUID, login: str, challenge: bytes
    ) -> dict[str, object]:
        options = generate_registration_options(
            rp_id=rp_id,
            rp_name="FraudLens",
            user_id=account_id.bytes,
            user_name=login,
            challenge=challenge,
            timeout=120_000,
            authenticator_selection=AuthenticatorSelectionCriteria(
                user_verification=UserVerificationRequirement.REQUIRED
            ),
        )
        return cast(dict[str, object], json.loads(options_to_json(options)))

    def verify_registration(
        self, *, response: dict[str, object], challenge: bytes, rp_id: str, origin: str
    ) -> VerifiedMfaCredential:
        try:
            verified = verify_registration_response(
                credential=response,
                expected_challenge=challenge,
                expected_rp_id=rp_id,
                expected_origin=origin,
                require_user_presence=True,
                require_user_verification=True,
            )
        except (InvalidRegistrationResponse, ValueError, TypeError) as exc:
            raise InvalidMfaResponse("invalid authenticator response") from exc
        return VerifiedMfaCredential(
            verified.credential_id,
            verified.credential_public_key,
            verified.sign_count,
            verified.credential_device_type.value,
            verified.credential_backed_up,
        )

    def authentication_options(
        self, *, rp_id: str, challenge: bytes, credential_ids: tuple[bytes, ...]
    ) -> dict[str, object]:
        options = generate_authentication_options(
            rp_id=rp_id,
            challenge=challenge,
            timeout=120_000,
            allow_credentials=[PublicKeyCredentialDescriptor(id=item) for item in credential_ids],
            user_verification=UserVerificationRequirement.REQUIRED,
        )
        return cast(dict[str, object], json.loads(options_to_json(options)))

    def verify_authentication(
        self,
        *,
        response: dict[str, object],
        challenge: bytes,
        rp_id: str,
        origin: str,
        credential: MfaCredential,
    ) -> int:
        try:
            verified = verify_authentication_response(
                credential=response,
                expected_challenge=challenge,
                expected_rp_id=rp_id,
                expected_origin=origin,
                credential_public_key=credential.public_key,
                credential_current_sign_count=credential.sign_count,
                require_user_verification=True,
            )
        except (InvalidAuthenticationResponse, ValueError, TypeError) as exc:
            raise InvalidMfaResponse("invalid authenticator response") from exc
        if verified.credential_id != credential.credential_id:
            raise InvalidMfaResponse("invalid authenticator response")
        return verified.new_sign_count

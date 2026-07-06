import pytest

pytest.importorskip("requests")

from google_photos import _pkce_s256_challenge, create_oauth_state, oauth_state_error


class TestOAuthState:
    def test_round_trip(self):
        state = create_oauth_state()
        assert oauth_state_error(state) is None

    def test_rejects_tampered_state(self):
        state = create_oauth_state()
        assert oauth_state_error(state + "x") is not None

    def test_pkce_challenge_is_url_safe(self):
        verifier = "test-verifier-string"
        challenge = _pkce_s256_challenge(verifier)
        assert "=" not in challenge
        assert len(challenge) > 20

    def test_payload_includes_pkce_verifier(self):
        state = create_oauth_state()
        from google_photos import _load_oauth_state

        payload = _load_oauth_state(state)
        assert payload.get("cv")
        assert len(payload["cv"]) >= 43

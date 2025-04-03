from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_round_trip():
    password_hash = hash_password("demo-clinical")

    assert verify_password("demo-clinical", password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_access_token_round_trip():
    token = create_access_token("user-1", {"role": "hospitalist"})
    payload = decode_access_token(token)

    assert payload["sub"] == "user-1"
    assert payload["role"] == "hospitalist"


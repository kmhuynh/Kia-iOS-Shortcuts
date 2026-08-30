import json

from hyundai_kia_connect_api.Token import Token


PERSISTED_TOKEN_FIELDS = (
    "access_token",
    "refresh_token",
    "device_id",
    "valid_until",
)


def _validate_token_data(token_data):
    required_fields = ("refresh_token", "device_id")
    missing_fields = [field for field in required_fields if not token_data.get(field)]
    if missing_fields:
        raise ValueError(
            "KIA_TOKEN_JSON is missing required fields: " + ", ".join(missing_fields)
        )


def token_to_json(token):
    token_data = token.to_dict()
    persisted_data = {
        field: token_data.get(field) for field in PERSISTED_TOKEN_FIELDS
    }
    _validate_token_data(persisted_data)
    return json.dumps(persisted_data, separators=(",", ":"))


def token_from_json(raw_token, username, password, pin):
    if not raw_token:
        return None

    try:
        token_data = json.loads(raw_token)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("KIA_TOKEN_JSON must contain valid JSON") from exc

    if not isinstance(token_data, dict):
        raise ValueError("KIA_TOKEN_JSON must contain a JSON object")

    _validate_token_data(token_data)

    token_data.update(
        {
            "username": username,
            "password": password,
            "pin": str(pin),
        }
    )
    return Token.from_dict(token_data)

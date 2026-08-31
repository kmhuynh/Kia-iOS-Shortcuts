import datetime as dt
import json

import pytest
from hyundai_kia_connect_api.Token import Token

from kia_token import token_from_json, token_to_json


def test_token_json_preserves_session_without_storing_account_credentials():
    valid_until = dt.datetime(2026, 9, 1, 12, 0, tzinfo=dt.UTC)
    token = Token(
        username="owner@example.com",
        password="kia-password",
        pin="1234",
        access_token="access-token",
        refresh_token="refresh-token",
        device_id="stable-device-id",
        valid_until=valid_until,
    )

    raw_token = token_to_json(token)
    serialized = json.loads(raw_token)

    assert serialized == {
        "access_token": "access-token",
        "refresh_token": "refresh-token",
        "device_id": "stable-device-id",
        "valid_until": "2026-09-01T12:00:00+00:00",
    }

    restored = token_from_json(
        raw_token,
        username="configured@example.com",
        password="configured-password",
        pin="9876",
    )
    assert restored.username == "configured@example.com"
    assert restored.password == "configured-password"
    assert restored.pin == "9876"
    assert restored.access_token == "access-token"
    assert restored.refresh_token == "refresh-token"
    assert restored.device_id == "stable-device-id"
    assert restored.valid_until == valid_until


def test_token_json_rejects_incomplete_session_data():
    with pytest.raises(ValueError, match="refresh_token, device_id"):
        token_from_json(
            '{"access_token":"access-token"}',
            username="owner@example.com",
            password="kia-password",
            pin="1234",
        )


def test_token_json_refuses_to_export_incomplete_session_data():
    with pytest.raises(ValueError, match="refresh_token"):
        token_to_json(Token(access_token="access-token", device_id="device-id"))

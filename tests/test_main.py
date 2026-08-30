import os
from unittest.mock import MagicMock

import pytest

os.environ.update(
    {
        "KIA_USERNAME": "test@example.com",
        "KIA_PASSWORD": "test-password",
        "KIA_PIN": "1234",
        "SECRET_KEY": "test-secret-key",
        "VEHICLE_ID": "sportage-vehicle-id",
        "KIA_TOKEN_JSON": "",
    }
)

import main


@pytest.fixture
def manager(monkeypatch):
    manager = MagicMock()
    monkeypatch.setattr(main, "vehicle_manager", manager)
    monkeypatch.setattr(main, "VEHICLE_ID", "sportage-vehicle-id")
    return manager


def test_start_climate_uses_sportage_preset_without_status_refresh(manager):
    manager.start_climate.return_value = "kia-transaction-id"

    with main.app.test_client() as client:
        response = client.post(
            "/start_climate",
            headers={"Authorization": "test-secret-key"},
        )

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "climate_started",
        "result": "kia-transaction-id",
    }
    manager.check_and_refresh_token.assert_called_once_with()
    manager.update_all_vehicles_with_cached_state.assert_not_called()
    manager.start_climate.assert_called_once()

    vehicle_id, options = manager.start_climate.call_args.args
    assert vehicle_id == "sportage-vehicle-id"
    assert options.set_temp == 70
    assert options.duration == 5
    assert options.climate is True
    assert options.defrost is False
    assert options.heating == 0
    assert options.steering_wheel == 0
    assert options.front_left_seat == 4
    assert options.front_right_seat == 4


def test_start_climate_rejects_requests_without_secret(manager):
    with main.app.test_client() as client:
        response = client.post("/start_climate")

    assert response.status_code == 403
    assert response.get_json() == {"error": "Unauthorized"}
    assert manager.method_calls == []


def test_start_climate_explains_how_to_restore_kia_authentication(manager):
    manager.check_and_refresh_token.side_effect = main.AuthenticationError(
        "OTP required"
    )

    with main.app.test_client() as client:
        response = client.post(
            "/start_climate",
            headers={"Authorization": "test-secret-key"},
        )

    assert response.status_code == 401
    assert response.get_json()["action"] == (
        "Run the token bootstrap and update KIA_TOKEN_JSON in Vercel"
    )
    manager.start_climate.assert_not_called()

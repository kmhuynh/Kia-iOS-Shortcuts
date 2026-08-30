from types import SimpleNamespace
from unittest.mock import MagicMock

from hyundai_kia_connect_api.const import OTP_NOTIFY_TYPE

from scripts.bootstrap_kia_token import complete_login


def test_complete_login_sends_and_verifies_otp():
    otp_request = SimpleNamespace(has_email=True, has_sms=False)
    manager = MagicMock()
    manager.login.return_value = otp_request
    manager.token = object()

    token = complete_login(
        manager,
        choose_channel=lambda request: OTP_NOTIFY_TYPE.EMAIL,
        read_code=lambda: "654321",
    )

    manager.send_otp.assert_called_once_with(OTP_NOTIFY_TYPE.EMAIL)
    manager.verify_otp_and_complete_login.assert_called_once_with("654321")
    assert token is manager.token


def test_complete_login_uses_existing_session_without_otp():
    manager = MagicMock()
    manager.login.return_value = True
    manager.token = object()
    choose_channel = MagicMock()
    read_code = MagicMock()

    token = complete_login(manager, choose_channel, read_code)

    manager.send_otp.assert_not_called()
    manager.verify_otp_and_complete_login.assert_not_called()
    choose_channel.assert_not_called()
    read_code.assert_not_called()
    assert token is manager.token

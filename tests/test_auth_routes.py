import importlib
import os
import sys
import types
import unittest


class AuthenticationError(Exception):
    pass


class AuthenticationOTPRequired(AuthenticationError):
    pass


class ClimateRequestOptions:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class OTP_NOTIFY_TYPE:
    EMAIL = "EMAIL"
    SMS = "SMS"


class FakeOTPRequest:
    has_email = True
    has_sms = True
    email = "k***@example.com"
    sms = "(***) ***-1234"


class FakeVehicleManager:
    login_result = True
    check_exception = None
    sent_otp = None
    verified_otp = None

    def __init__(self, **kwargs):
        self.vehicles = {}

    def check_and_refresh_token(self):
        if self.check_exception:
            raise self.check_exception
        return True

    def login(self):
        return self.login_result

    def send_otp(self, notify_type):
        self.__class__.sent_otp = notify_type

    def verify_otp_and_complete_login(self, otp_code):
        self.__class__.verified_otp = otp_code


def load_app():
    os.environ.update(
        {
            "KIA_USERNAME": "user@example.com",
            "KIA_PASSWORD": "password",
            "KIA_PIN": "1234",
            "SECRET_KEY": "secret",
        }
    )

    api_module = types.ModuleType("hyundai_kia_connect_api")
    api_module.VehicleManager = FakeVehicleManager
    api_module.ClimateRequestOptions = ClimateRequestOptions

    const_module = types.ModuleType("hyundai_kia_connect_api.const")
    const_module.OTP_NOTIFY_TYPE = OTP_NOTIFY_TYPE

    exceptions_module = types.ModuleType("hyundai_kia_connect_api.exceptions")
    exceptions_module.AuthenticationError = AuthenticationError
    exceptions_module.AuthenticationOTPRequired = AuthenticationOTPRequired

    sys.modules["hyundai_kia_connect_api"] = api_module
    sys.modules["hyundai_kia_connect_api.const"] = const_module
    sys.modules["hyundai_kia_connect_api.exceptions"] = exceptions_module
    sys.modules.pop("main", None)
    return importlib.import_module("main")


class AuthRouteTests(unittest.TestCase):
    def setUp(self):
        FakeVehicleManager.login_result = True
        FakeVehicleManager.check_exception = None
        FakeVehicleManager.sent_otp = None
        FakeVehicleManager.verified_otp = None
        self.main = load_app()
        self.client = self.main.app.test_client()

    def test_start_climate_tells_user_to_send_otp_when_kia_requires_otp(self):
        self.main.vehicle_manager.__class__.check_exception = (
            AuthenticationOTPRequired("OTP required to refresh token")
        )

        response = self.client.post(
            "/start_climate", headers={"Authorization": "secret"}
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["action"], "POST /send_otp first")

    def test_send_otp_starts_login_and_sends_email_by_default(self):
        self.main.vehicle_manager.__class__.login_result = FakeOTPRequest()

        response = self.client.post("/send_otp", headers={"Authorization": "secret"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "otp_sent")
        self.assertEqual(FakeVehicleManager.sent_otp, OTP_NOTIFY_TYPE.EMAIL)

    def test_verify_otp_completes_login(self):
        response = self.client.post(
            "/verify_otp",
            headers={"Authorization": "secret"},
            json={"otp": "123456"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "authenticated")
        self.assertEqual(FakeVehicleManager.verified_otp, "123456")


if __name__ == "__main__":
    unittest.main()

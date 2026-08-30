import getpass
import os

from hyundai_kia_connect_api import VehicleManager
from hyundai_kia_connect_api.const import OTP_NOTIFY_TYPE

from kia_token import token_to_json


def complete_login(manager, choose_channel, read_code):
    login_result = manager.login()
    if login_result is True:
        return manager.token

    notify_type = choose_channel(login_result)
    manager.send_otp(notify_type)
    manager.verify_otp_and_complete_login(read_code())
    return manager.token


def read_required_value(environment_name, prompt, secret=False):
    value = os.environ.get(environment_name)
    if value:
        return value

    reader = getpass.getpass if secret else input
    value = reader(prompt).strip()
    if not value:
        raise SystemExit(f"{environment_name} is required")
    return value


def choose_otp_channel(otp_request):
    channels = []
    if otp_request.has_email:
        channels.append((OTP_NOTIFY_TYPE.EMAIL, f"email ({otp_request.email})"))
    if otp_request.has_sms:
        channels.append((OTP_NOTIFY_TYPE.SMS, f"SMS ({otp_request.sms})"))

    if not channels:
        raise SystemExit("Kia requested OTP but did not provide a delivery method")
    if len(channels) == 1:
        print(f"Sending OTP by {channels[0][1]}.")
        return channels[0][0]

    print("Available OTP delivery methods:")
    for index, (_, label) in enumerate(channels, start=1):
        print(f"  {index}. {label}")

    while True:
        choice = input("Choose a delivery method: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(channels):
            return channels[int(choice) - 1][0]
        print("Enter one of the listed numbers.")


def read_otp_code():
    code = input("Enter the Kia OTP code: ").strip()
    if not code:
        raise SystemExit("OTP code is required")
    return code


def main():
    username = read_required_value("KIA_USERNAME", "Kia email: ")
    password = read_required_value("KIA_PASSWORD", "Kia password: ", secret=True)
    pin = read_required_value("KIA_PIN", "Kia PIN: ", secret=True)

    manager = VehicleManager(
        region=3,
        brand=1,
        username=username,
        password=password,
        pin=pin,
    )
    token = complete_login(manager, choose_otp_channel, read_otp_code)

    print("\nAdd a Vercel environment variable named KIA_TOKEN_JSON")
    print("with this exact value, then redeploy the project:\n")
    print(token_to_json(token))


if __name__ == "__main__":
    main()

import os
from flask import Flask, request, jsonify
from hyundai_kia_connect_api import VehicleManager, ClimateRequestOptions
from hyundai_kia_connect_api.const import OTP_NOTIFY_TYPE
from hyundai_kia_connect_api.exceptions import AuthenticationError, AuthenticationOTPRequired
from kia_token import token_from_json

app = Flask(__name__)

# =========================
# Environment Variables
# =========================
USERNAME = os.environ.get("KIA_USERNAME")
PASSWORD = os.environ.get("KIA_PASSWORD")
PIN = os.environ.get("KIA_PIN")
SECRET_KEY = os.environ.get("SECRET_KEY")
VEHICLE_ID = os.environ.get("VEHICLE_ID")  # Optional
KIA_TOKEN_JSON = os.environ.get("KIA_TOKEN_JSON")  # Optional, recommended for USA
AUTH_RECOVERY_ACTION = (
    "Run the token bootstrap and update KIA_TOKEN_JSON in Vercel"
)

missing = []
if not USERNAME:
    missing.append("KIA_USERNAME")
if not PASSWORD:
    missing.append("KIA_PASSWORD")
if not PIN:
    missing.append("KIA_PIN")
if not SECRET_KEY:
    missing.append("SECRET_KEY")

if missing:
    raise ValueError(f"Missing environment variables: {', '.join(missing)}")

# =========================
# Vehicle Manager
# =========================
saved_token = token_from_json(
    KIA_TOKEN_JSON,
    username=USERNAME,
    password=PASSWORD,
    pin=PIN,
)

vehicle_manager = VehicleManager(
    region=3,  # North America
    brand=1,   # KIA
    username=USERNAME,
    password=PASSWORD,
    pin=str(PIN),
    token=saved_token,
)

# =========================
# Helper Functions
# =========================
def authorize_request():
    return request.headers.get("Authorization") == SECRET_KEY


def ensure_authenticated():
    """
    Attempt to refresh Kia token.
    Will fail if Kia requires OTP / captcha.
    """
    try:
        vehicle_manager.check_and_refresh_token()
    except AuthenticationOTPRequired:
        raise
    except AuthenticationError as e:
        raise AuthenticationError(
            "Kia authentication failed."
        ) from e


def refresh_and_sync():
    """
    Refresh token and sync vehicle state
    """
    ensure_authenticated()
    vehicle_manager.update_all_vehicles_with_cached_state()


def get_vehicle_id():
    """
    Return VEHICLE_ID if provided, otherwise
    dynamically select the first vehicle.
    """
    if VEHICLE_ID:
        return VEHICLE_ID

    vehicles = vehicle_manager.vehicles
    if not vehicles:
        raise ValueError("No vehicles found on the Kia account.")

    first_vehicle_id = next(iter(vehicles.keys()))
    return first_vehicle_id


def sportage_climate_options():
    return ClimateRequestOptions(
        set_temp=70,
        duration=5,
        climate=True,
        defrost=False,
        heating=0,
        steering_wheel=0,
        front_left_seat=4,
        front_right_seat=4,
    )


def summer_climate_options():
    """Cool the cabin to 70F for 10 minutes with seats on max ventilation."""
    return ClimateRequestOptions(
        set_temp=70,
        duration=10,
        climate=True,
        defrost=False,
        heating=0,
        steering_wheel=0,
        front_left_seat=5,   # High Cool
        front_right_seat=5,  # High Cool
    )


def winter_climate_options():
    """Warm the cabin to 78F for 10 minutes with seat, wheel and glass heat."""
    return ClimateRequestOptions(
        set_temp=78,
        duration=10,
        climate=True,
        defrost=True,
        heating=1,           # rear window defogger + heated side mirrors
        steering_wheel=1,    # heated steering wheel
        front_left_seat=8,   # High Heat
        front_right_seat=8,  # High Heat
    )


def otp_response(message):
    return jsonify({
        "error": "Authentication failed",
        "details": message,
        "action": "POST /send_otp first"
    }), 401


def authentication_failed_response(error):
    return jsonify({
        "error": "Authentication failed",
        "details": str(error),
        "action": AUTH_RECOVERY_ACTION
    }), 401


def parse_notify_type():
    body = request.get_json(silent=True) or {}
    notify_type = str(body.get("notify_type", "EMAIL")).upper()
    if notify_type in ("SMS", "PHONE"):
        return OTP_NOTIFY_TYPE.SMS
    if notify_type == "EMAIL":
        return OTP_NOTIFY_TYPE.EMAIL
    raise ValueError("notify_type must be EMAIL or SMS")


def otp_request_json(otp_request):
    return {
        "has_email": getattr(otp_request, "has_email", None),
        "email": getattr(otp_request, "email", None),
        "has_sms": getattr(otp_request, "has_sms", None),
        "sms": getattr(otp_request, "sms", None),
    }


# =========================
# Logging
# =========================
@app.before_request
def log_request_info():
    print(f"Incoming request: {request.method} {request.path}")


# =========================
# Routes
# =========================
@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "status": "OK",
        "service": "Kia Vehicle Control API"
    }), 200


@app.route("/auth_status", methods=["GET"])
def auth_status():
    if not authorize_request():
        return jsonify({"error": "Unauthorized"}), 403

    try:
        ensure_authenticated()
        return jsonify({"status": "authenticated"}), 200
    except AuthenticationOTPRequired as e:
        return otp_response(str(e))
    except AuthenticationError as e:
        return authentication_failed_response(e)


@app.route("/send_otp", methods=["POST"])
def send_otp():
    if not authorize_request():
        return jsonify({"error": "Unauthorized"}), 403

    try:
        login_result = vehicle_manager.login()
        if login_result is True:
            return jsonify({"status": "authenticated"}), 200

        notify_type = parse_notify_type()
        vehicle_manager.send_otp(notify_type)

        return jsonify({
            "status": "otp_sent",
            "notify_type": getattr(notify_type, "value", notify_type),
            "otp": otp_request_json(login_result)
        }), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    except AuthenticationError as e:
        return authentication_failed_response(e)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    if not authorize_request():
        return jsonify({"error": "Unauthorized"}), 403

    body = request.get_json(silent=True) or {}
    otp_code = body.get("otp")
    if not otp_code:
        return jsonify({"error": "Missing otp"}), 400

    try:
        vehicle_manager.verify_otp_and_complete_login(str(otp_code))
        return jsonify({"status": "authenticated"}), 200

    except AuthenticationError as e:
        return authentication_failed_response(e)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/list_vehicles", methods=["GET"])
def list_vehicles():
    if not authorize_request():
        return jsonify({"error": "Unauthorized"}), 403

    try:
        refresh_and_sync()

        vehicles = vehicle_manager.vehicles
        if not vehicles:
            return jsonify({"error": "No vehicles found"}), 404

        vehicle_list = [
            {
                "name": v.name,
                "id": v.id,
                "model": v.model,
                "year": v.year
            }
            for v in vehicles.values()
        ]

        return jsonify({
            "status": "success",
            "vehicles": vehicle_list
        }), 200

    except AuthenticationOTPRequired as e:
        return otp_response(str(e))

    except AuthenticationError as e:
        return authentication_failed_response(e)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/find_vehicle", methods=["GET"])
def find_vehicle():
    if not authorize_request():
        return jsonify({"error": "Unauthorized"}), 403

    try:
        refresh_and_sync()
        vehicle = vehicle_manager.get_vehicle(get_vehicle_id())

        latitude = vehicle.location_latitude
        longitude = vehicle.location_longitude
        if latitude is None or longitude is None:
            return jsonify({"error": "Kia reported no location for this vehicle"}), 404

        located_at = vehicle.location_last_updated_at

        return jsonify({
            "status": "success",
            "latitude": latitude,
            "longitude": longitude,
            "maps_url": f"https://maps.apple.com/?ll={latitude},{longitude}&q=Sportage",
            "located_at": located_at.isoformat() if located_at else None,
        }), 200

    except AuthenticationOTPRequired as e:
        return otp_response(str(e))

    except AuthenticationError as e:
        return authentication_failed_response(e)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def run_climate_preset(climate_options):
    """Send one climate preset to the car. Shared by the climate routes."""
    if not authorize_request():
        return jsonify({"error": "Unauthorized"}), 403

    try:
        ensure_authenticated()
        vehicle_id = get_vehicle_id()

        result = vehicle_manager.start_climate(vehicle_id, climate_options)

        return jsonify({
            "status": "climate_started",
            "result": result
        }), 200

    except AuthenticationOTPRequired as e:
        return otp_response(str(e))

    except AuthenticationError as e:
        return authentication_failed_response(e)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/start_climate", methods=["POST"])
def start_climate():
    return run_climate_preset(sportage_climate_options())


@app.route("/summer_climate", methods=["POST"])
def summer_climate():
    return run_climate_preset(summer_climate_options())


@app.route("/winter_climate", methods=["POST"])
def winter_climate():
    return run_climate_preset(winter_climate_options())


@app.route("/stop_climate", methods=["POST"])
def stop_climate():
    if not authorize_request():
        return jsonify({"error": "Unauthorized"}), 403

    try:
        refresh_and_sync()
        vehicle_id = get_vehicle_id()

        result = vehicle_manager.stop_climate(vehicle_id)

        return jsonify({
            "status": "climate_stopped",
            "result": result
        }), 200

    except AuthenticationOTPRequired as e:
        return otp_response(str(e))

    except AuthenticationError as e:
        return authentication_failed_response(e)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/unlock_car", methods=["POST"])
def unlock_car():
    if not authorize_request():
        return jsonify({"error": "Unauthorized"}), 403

    try:
        refresh_and_sync()
        vehicle_id = get_vehicle_id()

        result = vehicle_manager.unlock(vehicle_id)

        return jsonify({
            "status": "car_unlocked",
            "result": result
        }), 200

    except AuthenticationOTPRequired as e:
        return otp_response(str(e))

    except AuthenticationError as e:
        return authentication_failed_response(e)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/lock_car", methods=["POST"])
def lock_car():
    if not authorize_request():
        return jsonify({"error": "Unauthorized"}), 403

    try:
        refresh_and_sync()
        vehicle_id = get_vehicle_id()

        result = vehicle_manager.lock(vehicle_id)

        return jsonify({
            "status": "car_locked",
            "result": result
        }), 200

    except AuthenticationOTPRequired as e:
        return otp_response(str(e))

    except AuthenticationError as e:
        return authentication_failed_response(e)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# App Entry
# =========================
if __name__ == "__main__":
    print("Starting Kia Vehicle Control API...")
    app.run(host="0.0.0.0", port=8080)

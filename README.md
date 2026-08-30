# Kia Sportage One-Tap Climate Shortcut

This project connects an iOS Shortcut to Kia Connect through a small Flask API hosted on Vercel. One tap sends this fixed remote-start profile to a US Kia vehicle:

- Cabin temperature: 70 F
- Duration: 5 minutes
- Driver seat ventilation: level 2
- Front passenger seat ventilation: level 2
- Defroster, heated accessories, and steering-wheel heat: off

The API uses the unofficial [Hyundai Kia Connect API](https://github.com/Hyundai-Kia-Connect/hyundai_kia_connect_api). Kia can change its authentication or command APIs without notice.

## How It Works

```text
iOS Shortcut -> Vercel Flask API -> Kia Connect -> Vehicle
```

The Shortcut holds only the Vercel URL and a random API secret. Your Kia username, password, and PIN remain in Vercel environment variables.

## Deploy to Vercel

### 1. Import the repository

1. Sign in to [Vercel](https://vercel.com/).
2. Select **Add New > Project**.
3. Import `kmhuynh/Kia-iOS-Shortcuts` from GitHub.
4. Keep the default build settings. Vercel reads the Python requirement and dependencies from this repository.

### 2. Add environment variables

Add these variables in the Vercel project settings:

| Variable | Value |
| --- | --- |
| `KIA_USERNAME` | Email used for Kia Access |
| `KIA_PASSWORD` | Kia Access password |
| `KIA_PIN` | Kia remote-command PIN |
| `SECRET_KEY` | A long random secret used only by the Shortcut |
| `VEHICLE_ID` | Kia vehicle ID; optional for an account with exactly one vehicle |
| `KIA_TOKEN_JSON` | Durable Kia session produced by the bootstrap command below |

Generate a strong secret on a Mac with:

```bash
openssl rand -hex 32
```

Do not put the Kia password or PIN in the iOS Shortcut.

### 3. Bootstrap the Kia session

Kia USA can require OTP for a new API device. A Vercel function cannot complete that interactive step on its own, so create the session once from this repository on the Mac:

```bash
uv sync
uv run python -m scripts.bootstrap_kia_token
```

The command reads `KIA_USERNAME`, `KIA_PASSWORD`, and `KIA_PIN` from your local environment when available. Otherwise, it prompts for them. It then sends an OTP using the email address or phone number registered with Kia.

After verification, the command prints a compact JSON value. Create the `KIA_TOKEN_JSON` environment variable in Vercel with that exact value, then redeploy. The JSON contains Kia session tokens and a device identifier, but not your username, password, or PIN. Treat it as a secret.

### 4. Verify the deployment

Open the assigned Vercel URL. The root response should report `status: OK`.

To list vehicles and obtain `VEHICLE_ID`:

```bash
curl -H "Authorization: YOUR_SECRET_KEY" \
  https://YOUR_PROJECT.vercel.app/list_vehicles
```

After setting `VEHICLE_ID`, test the climate command:

```bash
curl -X POST \
  -H "Authorization: YOUR_SECRET_KEY" \
  https://YOUR_PROJECT.vercel.app/start_climate
```

A successful request returns JSON containing `"status": "climate_started"` and a Kia transaction identifier. The vehicle can take approximately 10-30 seconds to receive the command.

## Create the iOS Shortcut

1. Open **Shortcuts** on the iPhone and tap **+**.
2. Add the **Get Contents of URL** action.
3. Set the URL to `https://YOUR_PROJECT.vercel.app/start_climate`.
4. Expand the action and set **Method** to **POST**.
5. Under **Headers**, add `Authorization` with the exact value of `SECRET_KEY`.
6. Add **Get Dictionary Value** and retrieve `status` from **Contents of URL**.
7. Add an **If** action checking whether `status` is `climate_started`.
8. In the success branch, add **Show Notification** with `Sportage climate started`.
9. In the **Otherwise** branch, add **Show Result** using **Contents of URL** so authentication or Kia API errors remain visible.
10. Name the Shortcut `Start Sportage Climate`.
11. From the Shortcut details, add it to the Home Screen, a widget, or the Action Button.

The Shortcut sends no request body; the climate profile is fixed in `main.py`.

## Climate Configuration

The `/start_climate` route uses:

```python
ClimateRequestOptions(
    set_temp=70,
    duration=5,
    climate=True,
    defrost=False,
    heating=0,
    steering_wheel=0,
    front_left_seat=4,
    front_right_seat=4,
)
```

For Kia USA, seat value `4` maps to medium cooling, which corresponds to ventilation level 2. Authentication is checked before the command, but the route skips an unnecessary vehicle-status refresh to reduce latency.

## Other Endpoints

All control and vehicle-list endpoints require the same `Authorization` header.

| Method | Endpoint | Action |
| --- | --- | --- |
| `GET` | `/auth_status` | Check Kia authentication |
| `GET` | `/list_vehicles` | List vehicles and IDs |
| `POST` | `/start_climate` | Start the fixed climate profile |
| `POST` | `/stop_climate` | Stop remote climate |
| `POST` | `/lock_car` | Lock the vehicle |
| `POST` | `/unlock_car` | Unlock the vehicle |

## Limitations and Safety

- Kia may eventually expire or revoke the refresh token. If the API returns an authentication error, rerun the bootstrap command, replace `KIA_TOKEN_JSON`, and redeploy.
- Vercel cold starts and Kia's cloud-to-vehicle connection add some delay. The Shortcut removes app navigation; it does not make the vehicle receive commands instantly.
- Remote commands require an active Kia Connect subscription and cellular coverage for both Kia's service and the vehicle.
- Never use remote climate control or remote start in an enclosed or partially enclosed area without proper ventilation.
- Keep `SECRET_KEY` private. Anyone who has it can call the deployed vehicle-control endpoints.

## Local Tests

```bash
uv sync
uv run pytest -v
```

Tests mock the Kia vehicle manager and never contact Kia or start the vehicle.

## License

This project is licensed under the MIT License. See `LICENSE` for details.

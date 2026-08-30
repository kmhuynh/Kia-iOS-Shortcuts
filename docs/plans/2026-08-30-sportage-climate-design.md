# Sportage One-Tap Climate Design

## Goal

Provide a one-tap iOS Shortcut that requests a fixed remote climate profile for a US 2026 Kia Sportage Hybrid SX Prestige: 70 degrees Fahrenheit, five minutes, and medium ventilation for both front seats.

## Architecture

The iOS Shortcut sends an authenticated HTTP POST to the existing Flask `/start_climate` route hosted on Vercel. The Flask service authenticates with Kia Connect through `hyundai-kia-connect-api`, selects the configured vehicle, and submits the fixed climate request. Kia Connect then delivers the command to the vehicle over its cellular connection.

The Shortcut stores only the Vercel URL and a random API secret. Kia credentials and PIN remain Vercel environment variables.

## Climate Profile

The route constructs `ClimateRequestOptions` with:

- `set_temp=70`
- `duration=5`
- `climate=True`
- `defrost=False`
- `heating=0`
- `steering_wheel=0`
- `front_left_seat=4`
- `front_right_seat=4`

For Kia USA, seat value `4` maps to medium cooling/ventilation. Rear-seat values are left unspecified; the upstream client serializes them as off when front-seat climate is included.

## Fast Path

The start route calls `ensure_authenticated()` and then sends the command. It does not request a vehicle-status refresh first. Authentication already initializes the vehicle list when required, and a configured `VEHICLE_ID` avoids selection ambiguity. Other routes retain their current synchronization behavior.

## Responses

On success, the route returns HTTP 200 with `status: climate_started` and the Kia transaction identifier. Unauthorized requests return HTTP 403. Authentication failures return HTTP 401 with a useful action message, and unexpected Kia/API failures return HTTP 500.

The iOS Shortcut displays a concise success or failure notification from the HTTP result.

## Testing

Flask route tests replace the real vehicle manager with a mock. Tests verify authorization, the exact climate profile, the absence of a status-refresh call on the start path, the selected vehicle ID, and the success response. No test contacts Kia or starts the vehicle.

## Limitations

This relies on an unofficial, reverse-engineered Kia API and may need maintenance when Kia changes authentication or command payloads. Kia may require OTP or app interaction after an authentication change. The Shortcut removes navigation steps but does not remove Kia's normal cloud-to-vehicle delay.

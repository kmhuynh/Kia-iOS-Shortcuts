# Sportage One-Tap Climate Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Customize the Vercel-backed iOS Shortcut API to start a 2026 Kia Sportage at 70 degrees Fahrenheit for five minutes with both front seats ventilated at level 2.

**Architecture:** Keep the existing Flask/Vercel bridge and its environment-variable authentication. Make the start-climate route construct one fixed, explicitly tested `ClimateRequestOptions` profile and skip the unnecessary vehicle-status refresh before submitting the command.

**Tech Stack:** Python 3.11+, Flask, `hyundai-kia-connect-api`, pytest, Vercel Python runtime, iOS Shortcuts

---

### Task 1: Add Route Test Infrastructure

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Create: `tests/test_main.py`

**Step 1: Add pytest as a development dependency**

Run: `uv add --dev "pytest>=8.3,<9"`

Expected: `pyproject.toml` gains a `dev` dependency group and `uv.lock` records pytest without changing runtime requirements.

**Step 2: Write the failing start-climate route test**

Create `tests/test_main.py` with environment variables set before importing `main`, replace `main.vehicle_manager` with a `MagicMock`, call the route through Flask's test client, and assert:

```python
assert response.status_code == 200
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
```

Also assert the JSON success status and transaction ID.

**Step 3: Run the focused test to verify it fails**

Run: `uv run pytest tests/test_main.py::test_start_climate_uses_sportage_preset_without_status_refresh -v`

Expected: FAIL because the current route refreshes vehicle status and still uses 72 degrees for ten minutes without seat settings.

**Step 4: Commit the failing test**

```bash
git add pyproject.toml uv.lock tests/test_main.py
git commit -m "test: specify Sportage climate shortcut profile"
```

### Task 2: Implement the Fixed Fast Climate Command

**Files:**
- Modify: `main.py`
- Test: `tests/test_main.py`

**Step 1: Add a preset constructor**

Add a small helper returning:

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

**Step 2: Use the authentication-only path**

In `/start_climate`, replace `refresh_and_sync()` with `ensure_authenticated()`, obtain the vehicle ID, construct the preset, and submit it. Do not change synchronization behavior for the listing, stop, lock, or unlock routes.

**Step 3: Run the focused test**

Run: `uv run pytest tests/test_main.py::test_start_climate_uses_sportage_preset_without_status_refresh -v`

Expected: PASS.

**Step 4: Add authorization coverage**

Add a test that posts without the `Authorization` header and asserts HTTP 403 plus `{"error": "Unauthorized"}`. Assert no Kia manager method is called.

**Step 5: Run all tests**

Run: `uv run pytest -v`

Expected: 2 tests pass.

**Step 6: Commit the implementation**

```bash
git add main.py tests/test_main.py
git commit -m "feat: add one-tap Sportage climate preset"
```

### Task 3: Document Deployment and the iOS Shortcut

**Files:**
- Modify: `README.md`

**Step 1: Update the project purpose and preset**

Document that `/start_climate` is customized for 70 degrees Fahrenheit, five minutes, and medium ventilation for both front seats. Explain that seat code `4` is the upstream Kia USA medium-cooling value.

**Step 2: Tighten deployment guidance**

Recommend setting `VEHICLE_ID`, generating a long random `SECRET_KEY`, and storing all Kia credentials only in Vercel environment variables. Note that the integration is unofficial and OTP/authentication changes can interrupt commands.

**Step 3: Give exact Shortcut actions**

Document the POST URL, `Authorization` header, success/failure notification behavior, and Home Screen/widget placement. Include Kia's enclosed-space remote-start warning.

**Step 4: Run verification**

Run: `uv run pytest -v`

Expected: all tests pass.

Run: `KIA_USERNAME=test KIA_PASSWORD=test KIA_PIN=1234 SECRET_KEY=test VEHICLE_ID=test uv run python -m py_compile main.py tests/test_main.py`

Expected: exit code 0.

**Step 5: Commit documentation**

```bash
git add README.md
git commit -m "docs: add one-tap iOS Shortcut setup"
```

### Task 4: Review the Final Branch

**Files:**
- Review: `main.py`
- Review: `tests/test_main.py`
- Review: `README.md`

**Step 1: Inspect the diff**

Run: `git diff main...HEAD --check`

Expected: no whitespace errors.

Run: `git diff main...HEAD --stat`

Expected: changes are limited to the design/plan, test setup, climate behavior, and README.

**Step 2: Run final verification**

Run: `uv run pytest -v`

Expected: all tests pass.

**Step 3: Confirm branch state**

Run: `git status --short --branch`

Expected: clean `feature/sportage-climate` branch.

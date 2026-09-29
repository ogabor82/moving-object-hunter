"""IMCCE SkyBoT cone search client.

Official documentation:
https://ssp.imcce.fr/webservices/skybot/api/conesearch/

- Epoch is UTC (SkyBoT query form: "Epoch (UTC)"), sent as Julian Day.
- RA/Dec are J2000 equatorial degrees (-refsys=EQJ2000); returned positions
  are astrometric J2000 relative to the observer (-observer, IAU code).
- The default observer is the geocenter (500). ZTF is MPC code I41
  (Palomar Mountain--ZTF); the topocentric parallax of main-belt objects
  is arcseconds, so ZTF frames must use I41.
- SkyBoT drops objects whose position error exceeds -filter (default 120
  arcsec). We send 0 (no filter) and keep the error as metadata instead.

Observed service behaviour (live, 2026-09): no objects -> HTTP 204 with an
empty body; bad request -> HTTP 400 with {"flag": -1, ...}; some server
errors -> HTTP 200 with {"flag": -1, ...}. Only a JSON list is a result.
"""

from typing import Any

import httpx


SKYBOT_CONESEARCH_URL = "https://ssp.imcce.fr/webservices/skybot/api/conesearch.php"
ZTF_OBSERVATORY_CODE = "I41"
GEOCENTER_OBSERVATORY_CODE = "500"
SKYBOT_CLIENT_NAME = "MovingObjectHunter"
# -rd limit from the SkyBoT documentation.
MAX_SEARCH_RADIUS_DEGREES = 10.0
# Covered epochs from the SkyBoT documentation (1889-11-13 .. 2060-03-21).
MIN_EPOCH_JD = 2411320.0
MAX_EPOCH_JD = 2473540.0


class SkyBoTServiceError(RuntimeError):
    """Raised when SkyBoT cannot answer; never means "no known objects"."""


def query_skybot_cone(
    ra_degrees: float,
    dec_degrees: float,
    radius_degrees: float,
    epoch_jd_utc: float,
    observer: str = ZTF_OBSERVATORY_CODE,
    client: httpx.Client | None = None,
    timeout_seconds: float = 120.0,
) -> list[dict[str, Any]]:
    """Return SkyBoT's raw known-object rows for a field at an epoch.

    An empty list means SkyBoT answered that no known object is in the
    field. Any failure (timeout, HTTP error, SkyBoT error flag, unexpected
    payload) raises SkyBoTServiceError.
    """
    _validate_query(ra_degrees, dec_degrees, radius_degrees, epoch_jd_utc)
    params = {
        "-ep": f"{epoch_jd_utc:.8f}",
        "-ra": f"{ra_degrees:.8f}",
        "-dec": f"{dec_degrees:.8f}",
        "-rd": f"{radius_degrees:.8f}",
        "-mime": "json",
        "-output": "basic",
        "-observer": observer,
        "-filter": "0",
        "-objFilter": "111",
        "-refsys": "EQJ2000",
        "-from": SKYBOT_CLIENT_NAME,
    }
    request = client.get if client is not None else httpx.get

    try:
        response = request(
            SKYBOT_CONESEARCH_URL, params=params, timeout=timeout_seconds
        )
    except httpx.TimeoutException as exc:
        raise SkyBoTServiceError(f"SkyBoT request timed out: {exc}") from exc
    except httpx.HTTPError as exc:
        raise SkyBoTServiceError(f"SkyBoT request failed: {exc}") from exc

    if response.status_code == 204:
        return []
    if response.status_code != 200:
        raise SkyBoTServiceError(
            f"SkyBoT request failed with HTTP {response.status_code}: "
            f"{_error_message(response)}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise SkyBoTServiceError("SkyBoT response is not valid JSON.") from exc

    if isinstance(payload, dict):
        raise SkyBoTServiceError(
            "SkyBoT reported an error: "
            f"{str(payload.get('message', payload))[:300]}"
        )
    if not isinstance(payload, list) or not all(
        isinstance(row, dict) for row in payload
    ):
        raise SkyBoTServiceError("SkyBoT response has an unexpected structure.")
    return payload


def _validate_query(
    ra_degrees: float,
    dec_degrees: float,
    radius_degrees: float,
    epoch_jd_utc: float,
) -> None:
    # SkyBoT does not reliably reject out-of-range input (observed: RA=400
    # crashes the JSON endpoint and is silently wrapped by the text one).
    if not 0.0 <= ra_degrees < 360.0:
        raise ValueError("ra_degrees must be in [0, 360).")
    if not -90.0 <= dec_degrees <= 90.0:
        raise ValueError("dec_degrees must be in [-90, 90].")
    if not 0.0 < radius_degrees <= MAX_SEARCH_RADIUS_DEGREES:
        raise ValueError(
            f"radius_degrees must be in (0, {MAX_SEARCH_RADIUS_DEGREES}]."
        )
    if not MIN_EPOCH_JD <= epoch_jd_utc <= MAX_EPOCH_JD:
        raise ValueError("epoch_jd_utc is outside the SkyBoT epoch range.")


def _error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:300]
    if isinstance(payload, dict) and "message" in payload:
        return str(payload["message"])[:300]
    return response.text[:300]

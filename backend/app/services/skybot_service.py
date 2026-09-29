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
errors -> HTTP 200 with {"flag": -1, ...}, intermittently for queries that
succeed on retry. Only a JSON list is a result.
"""

import time
from collections.abc import Callable
from typing import Any

import astropy.units as u
import httpx
from astropy.coordinates import Angle
from pydantic import ValidationError

from app.models.known_object import (
    KnownObjectEphemeris,
    KnownObjectField,
    RejectedSkyBoTRow,
)


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


class _TransientSkyBoTError(SkyBoTServiceError):
    """A SkyBoT failure worth retrying."""


def query_skybot_cone(
    ra_degrees: float,
    dec_degrees: float,
    radius_degrees: float,
    epoch_jd_utc: float,
    observer: str = ZTF_OBSERVATORY_CODE,
    client: httpx.Client | None = None,
    timeout_seconds: float = 120.0,
    max_attempts: int = 3,
    retry_delay_seconds: float = 2.0,
) -> list[dict[str, Any]]:
    """Return SkyBoT's raw known-object rows for a field at an epoch.

    An empty list means SkyBoT answered that no known object is in the
    field. Any failure (timeout, HTTP error, SkyBoT error flag, unexpected
    payload) raises SkyBoTServiceError. Transient failures (timeouts,
    connection errors, HTTP 5xx, error flag on HTTP 200) are retried up to
    `max_attempts` times in total.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1.")
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

    for attempt in range(1, max_attempts + 1):
        try:
            return _query_once(request, params, timeout_seconds)
        except _TransientSkyBoTError as exc:
            if attempt == max_attempts:
                raise SkyBoTServiceError(
                    f"{exc} (after {max_attempts} attempt(s))"
                ) from exc
            time.sleep(retry_delay_seconds)
    raise AssertionError("unreachable")


def _query_once(
    request: Callable[..., httpx.Response],
    params: dict[str, str],
    timeout_seconds: float,
) -> list[dict[str, Any]]:
    try:
        response = request(
            SKYBOT_CONESEARCH_URL, params=params, timeout=timeout_seconds
        )
    except httpx.TimeoutException as exc:
        raise _TransientSkyBoTError(f"SkyBoT request timed out: {exc}") from exc
    except httpx.HTTPError as exc:
        raise _TransientSkyBoTError(f"SkyBoT request failed: {exc}") from exc

    if response.status_code == 204:
        return []
    if response.status_code != 200:
        error_type = (
            _TransientSkyBoTError
            if response.status_code >= 500
            else SkyBoTServiceError
        )
        raise error_type(
            f"SkyBoT request failed with HTTP {response.status_code}: "
            f"{_error_message(response)}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise SkyBoTServiceError("SkyBoT response is not valid JSON.") from exc

    if isinstance(payload, dict):
        # Observed live: intermittent server crashes (e.g. SIGBUS) reported
        # as HTTP 200 with flag -1; the same query succeeds on retry.
        raise _TransientSkyBoTError(
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


def normalize_skybot_rows(
    rows: list[dict[str, Any]],
) -> tuple[list[KnownObjectEphemeris], list[RejectedSkyBoTRow]]:
    """Map raw SkyBoT JSON rows to KnownObjectEphemeris.

    Field names follow the live JSON response ("RA (hms)", "DEC (dms)"),
    which differs from the documented "RA (hour)"/"DEC (deg)". Rows that
    cannot be parsed are returned as rejected instead of failing the field.
    """
    objects: list[KnownObjectEphemeris] = []
    rejected: list[RejectedSkyBoTRow] = []
    for index, row in enumerate(rows):
        try:
            objects.append(_normalize_row(row))
        except ValidationError as exc:
            rejected.append(
                RejectedSkyBoTRow(
                    row_index=index,
                    reason="; ".join(
                        f"{'.'.join(str(part) for part in error['loc'])}: "
                        f"{error['msg']}"
                        for error in exc.errors()
                    ),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            rejected.append(
                RejectedSkyBoTRow(row_index=index, reason=f"unreadable row: {exc!r}")
            )
    return objects, rejected


def query_known_objects(
    ra_degrees: float,
    dec_degrees: float,
    radius_degrees: float,
    epoch_jd_utc: float,
    observer: str = ZTF_OBSERVATORY_CODE,
    client: httpx.Client | None = None,
) -> KnownObjectField:
    """Query SkyBoT and return the normalized known objects of the field."""
    rows = query_skybot_cone(
        ra_degrees,
        dec_degrees,
        radius_degrees,
        epoch_jd_utc,
        observer=observer,
        client=client,
    )
    objects, rejected = normalize_skybot_rows(rows)
    return KnownObjectField(
        epoch_jd_utc=epoch_jd_utc,
        field_ra=ra_degrees,
        field_dec=dec_degrees,
        field_radius_degrees=radius_degrees,
        observer=observer,
        objects=objects,
        rejected_rows=rejected,
    )


def _normalize_row(row: dict[str, Any]) -> KnownObjectEphemeris:
    number = _parse_number(row.get("Num"))
    name = str(row["Name"]).strip()
    return KnownObjectEphemeris(
        designation=str(number) if number is not None else name,
        number=number,
        name=name,
        object_class=str(row["Class"]),
        predicted_ra=float(
            Angle(row["RA (hms)"], unit=u.hourangle).wrap_at(360 * u.deg).deg
        ),
        predicted_dec=float(Angle(row["DEC (dms)"], unit=u.deg).deg),
        v_magnitude=_optional_float(row.get("VMag (mag)")),
        position_error_arcsec=float(row["Err (arcsec)"]),
        distance_from_field_center_arcsec=float(row["d (arcsec)"]),
        motion_ra_cos_dec_arcsec_per_hour=float(row["dRA (arcsec/h)"]),
        motion_dec_arcsec_per_hour=float(row["dDEC (arcsec/h)"]),
        observer_distance_au=_optional_float(row.get("dg (ua)")),
        heliocentric_distance_au=_optional_float(row.get("dh (ua)")),
    )


def _parse_number(value: Any) -> int | None:
    if value is None or str(value).strip() in ("", "-"):
        return None
    return int(value)


def _optional_float(value: Any) -> float | None:
    if value is None or str(value).strip() in ("", "-"):
        return None
    return float(value)

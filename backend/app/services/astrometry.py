import math
from collections.abc import Sequence

import astropy.units as u
import numpy
from astropy.coordinates import SkyCoord, angular_separation
from numpy.typing import ArrayLike, NDArray


def angular_distance_arcsec(
    ra1_degrees: float,
    dec1_degrees: float,
    ra2_degrees: float,
    dec2_degrees: float,
) -> float:
    """Great-circle distance between two ICRS positions in arcseconds."""
    first = SkyCoord(ra1_degrees * u.deg, dec1_degrees * u.deg, frame="icrs")
    second = SkyCoord(ra2_degrees * u.deg, dec2_degrees * u.deg, frame="icrs")
    return float(first.separation(second).to_value(u.arcsec))


def mean_position(positions: Sequence[tuple[float, float]]) -> tuple[float, float]:
    """Mean of (ra, dec) positions via unit vectors (safe across RA = 0)."""
    x = y = z = 0.0
    for ra, dec in positions:
        ra_rad, dec_rad = math.radians(ra), math.radians(dec)
        x += math.cos(dec_rad) * math.cos(ra_rad)
        y += math.cos(dec_rad) * math.sin(ra_rad)
        z += math.sin(dec_rad)
    ra = math.degrees(math.atan2(y, x)) % 360.0
    dec = math.degrees(math.atan2(z, math.hypot(x, y)))
    return ra, dec


# Margin around a track and the smallest cutout of a track window [arcsec].
TRACK_MARGIN_ARCSEC = 30.0
MIN_TRACK_WINDOW_ARCSEC = 60.0


def track_window(
    positions: Sequence[tuple[float, float]],
) -> tuple[float, float, float]:
    """(centre ra, centre dec, square size in arcsec) of a cutout holding
    the whole track plus TRACK_MARGIN_ARCSEC, rounded up to 10", at least
    MIN_TRACK_WINDOW_ARCSEC (the blink-comparator cutout rule)."""
    center_ra, center_dec = mean_position(positions)
    extent = max(
        angular_distance_arcsec(center_ra, center_dec, ra, dec)
        for ra, dec in positions
    )
    size = max(
        MIN_TRACK_WINDOW_ARCSEC,
        10.0 * math.ceil((2 * extent + 2 * TRACK_MARGIN_ARCSEC) / 10.0),
    )
    return center_ra, center_dec, size


def find_pairs_within(
    ra1_degrees: ArrayLike,
    dec1_degrees: ArrayLike,
    ra2_degrees: ArrayLike,
    dec2_degrees: ArrayLike,
    radius_arcsec: float,
) -> tuple[NDArray[numpy.intp], NDArray[numpy.intp], NDArray[numpy.float64]]:
    """Find all position pairs from two lists within `radius_arcsec`.

    Returns (indices into list 1, indices into list 2, separations in
    arcsec). Exact great-circle test; candidates are pre-selected by a
    declination window, so RA wrap-around needs no special handling.
    Avoids astropy's search_around_sky, which requires SciPy.
    """
    ra1 = numpy.asarray(ra1_degrees, dtype=float)
    dec1 = numpy.asarray(dec1_degrees, dtype=float)
    ra2 = numpy.asarray(ra2_degrees, dtype=float)
    dec2 = numpy.asarray(dec2_degrees, dtype=float)
    radius_degrees = radius_arcsec / 3600.0

    order = numpy.argsort(dec2, kind="stable")
    sorted_dec2 = dec2[order]
    low = numpy.searchsorted(sorted_dec2, dec1 - radius_degrees, side="left")
    high = numpy.searchsorted(sorted_dec2, dec1 + radius_degrees, side="right")
    counts = high - low

    first = numpy.repeat(numpy.arange(len(ra1)), counts)
    offsets = numpy.arange(counts.sum()) - numpy.repeat(
        numpy.cumsum(counts) - counts, counts
    )
    second = order[numpy.repeat(low, counts) + offsets]

    separations = numpy.rad2deg(
        angular_separation(
            numpy.deg2rad(ra1[first]),
            numpy.deg2rad(dec1[first]),
            numpy.deg2rad(ra2[second]),
            numpy.deg2rad(dec2[second]),
        )
    ) * 3600.0
    within = separations <= radius_arcsec
    return first[within], second[within], separations[within]

import math

import pytest

from app.services.astrometry import angular_distance_arcsec


def test_zero_distance_for_identical_positions() -> None:
    assert angular_distance_arcsec(255.5, 12.3, 255.5, 12.3) == pytest.approx(0.0)


def test_one_arcsecond_along_declination() -> None:
    distance = angular_distance_arcsec(120.0, 10.0, 120.0, 10.0 + 1 / 3600)

    assert distance == pytest.approx(1.0, rel=1e-6)


def test_right_ascension_offset_scales_with_cos_declination() -> None:
    declination = 60.0
    distance = angular_distance_arcsec(
        120.0, declination, 120.0 + 10 / 3600, declination
    )

    assert distance == pytest.approx(
        10 * math.cos(math.radians(declination)), rel=1e-4
    )


def test_distance_across_ra_wrap_around() -> None:
    distance = angular_distance_arcsec(359.9999, 0.0, 0.0001, 0.0)

    assert distance == pytest.approx(0.72, rel=1e-6)


def test_distance_near_celestial_pole() -> None:
    distance = angular_distance_arcsec(0.0, 89.9999, 180.0, 89.9999)

    assert distance == pytest.approx(0.72, rel=1e-4)


def test_distance_is_symmetric() -> None:
    forward = angular_distance_arcsec(10.0, -20.0, 10.01, -20.02)
    backward = angular_distance_arcsec(10.01, -20.02, 10.0, -20.0)

    assert forward == pytest.approx(backward)

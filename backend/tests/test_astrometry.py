import math

import numpy
import pytest

from app.services.astrometry import angular_distance_arcsec, find_pairs_within


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


def brute_force_pairs(
    first: list[tuple[float, float]],
    second: list[tuple[float, float]],
    radius_arcsec: float,
) -> set[tuple[int, int]]:
    return {
        (i, j)
        for i, (ra1, dec1) in enumerate(first)
        for j, (ra2, dec2) in enumerate(second)
        if angular_distance_arcsec(ra1, dec1, ra2, dec2) <= radius_arcsec
    }


def test_find_pairs_within_matches_brute_force() -> None:
    rng = numpy.random.default_rng(42)
    first = list(
        zip(rng.uniform(120.0, 120.01, 80), rng.uniform(10.0, 10.01, 80))
    )
    second = list(
        zip(rng.uniform(120.0, 120.01, 90), rng.uniform(10.0, 10.01, 90))
    )

    indices1, indices2, separations = find_pairs_within(
        *zip(*first), *zip(*second), 5.0
    )

    assert set(zip(indices1.tolist(), indices2.tolist())) == brute_force_pairs(
        first, second, 5.0
    )
    for i, j, separation in zip(indices1, indices2, separations):
        assert separation == pytest.approx(
            angular_distance_arcsec(*first[i], *second[j]), abs=1e-6
        )


def test_find_pairs_within_handles_ra_wrap_around_and_pole() -> None:
    first = [(359.99999, 0.0), (0.0, 89.99999)]
    second = [(0.00001, 0.0), (180.0, 89.99999)]

    indices1, indices2, _ = find_pairs_within(*zip(*first), *zip(*second), 0.1)

    assert set(zip(indices1.tolist(), indices2.tolist())) == {(0, 0), (1, 1)}


def test_find_pairs_within_handles_empty_input() -> None:
    indices1, indices2, separations = find_pairs_within([], [], [1.0], [1.0], 1.0)

    assert len(indices1) == len(indices2) == len(separations) == 0

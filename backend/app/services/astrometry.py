import astropy.units as u
from astropy.coordinates import SkyCoord


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

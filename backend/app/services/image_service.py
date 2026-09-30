"""FITS cutout → browser-displayable 8-bit image, explicitly and reversibly.

The transformation is display-only and never changes the science data:

1. Stretch: ZScale limits (astropy.visualization.ZScaleInterval, IRAF
   zscale) computed per frame on the finite pixels, then a linear map of
   [vmin, vmax] to 0..255 with clipping. Non-finite pixels become 0.
   Per-frame limits compensate for sky-level differences between epochs,
   which is what a blink comparator needs; brightness is therefore not
   comparable between frames.
2. Orientation: the cutout keeps the parent image grid (IRSA IBE). The
   array is only transposed and/or flipped (no resampling) so that north
   is up and east is left, using the WCS at the cutout centre. The small
   residual rotation of the detector (ZTF validation fields: 0.2-1.4 deg)
   is reported, not corrected.
"""

import math
from dataclasses import dataclass
from io import BytesIO

import numpy
from astropy.io import fits
from astropy.visualization import ZScaleInterval
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales


STRETCH_METHOD = "zscale_linear"
ORIENTATION = "north_up_east_left"


class ImageRenderError(ValueError):
    """Raised when a FITS cutout cannot be turned into a display image."""


@dataclass(frozen=True)
class RenderedFrame:
    """An 8-bit display image with the metadata needed to interpret it.

    Pixel (column, row) = (0, 0) is the top-left corner; rows run from
    north to south and columns from east to west.
    """

    width: int
    height: int
    pixels: bytes
    vmin: float
    vmax: float
    pixel_scale_arcsec: float
    center_x: float
    center_y: float
    rotation_deg: float
    transform: tuple[str, ...]
    _wcs: WCS
    _transpose: bool
    _flip_rows: bool
    _flip_columns: bool
    _source_shape: tuple[int, int]

    def world_to_display(self, ra: float, dec: float) -> tuple[float, float]:
        """Display (column, row) of a sky position, 0-based, fractional."""
        x, y = self._wcs.world_to_pixel_values(ra, dec)
        return _to_display(
            float(x),
            float(y),
            self._source_shape,
            self._transpose,
            self._flip_rows,
            self._flip_columns,
        )


def render_cutout(
    payload: bytes,
    center_ra: float,
    center_dec: float,
) -> RenderedFrame:
    """Stretch and orient a FITS cutout (primary HDU with celestial WCS)."""
    try:
        with fits.open(BytesIO(payload), memmap=False) as hdul:
            data = hdul[0].data
            header = hdul[0].header
            if data is None or data.ndim != 2:
                raise ImageRenderError("FITS cutout has no 2-D primary image.")
            data = numpy.array(data, dtype=numpy.float64)
            wcs = WCS(header).celestial
    except (OSError, ValueError) as exc:
        if isinstance(exc, ImageRenderError):
            raise
        raise ImageRenderError(f"Invalid FITS cutout: {exc}") from exc
    if not wcs.has_celestial:
        raise ImageRenderError("FITS cutout has no celestial WCS.")

    finite = numpy.isfinite(data)
    if not finite.any():
        raise ImageRenderError("FITS cutout contains no finite pixels.")
    vmin, vmax = (float(v) for v in ZScaleInterval().get_limits(data[finite]))
    if not vmax > vmin:
        vmax = vmin + 1.0
    scaled = numpy.clip((data - vmin) / (vmax - vmin), 0.0, 1.0) * 255.0
    image = numpy.where(finite, numpy.round(scaled), 0.0).astype(numpy.uint8)

    transpose, flip_rows, flip_columns, rotation = _orientation(
        wcs, center_ra, center_dec
    )
    shape = image.shape
    if transpose:
        image = image.T
    if flip_rows:
        image = image[::-1, :]
    if flip_columns:
        image = image[:, ::-1]

    x, y = wcs.world_to_pixel_values(center_ra, center_dec)
    center_x, center_y = _to_display(
        float(x), float(y), shape, transpose, flip_rows, flip_columns
    )
    scales = proj_plane_pixel_scales(wcs) * 3600.0
    return RenderedFrame(
        width=image.shape[1],
        height=image.shape[0],
        pixels=numpy.ascontiguousarray(image).tobytes(),
        vmin=vmin,
        vmax=vmax,
        pixel_scale_arcsec=float(numpy.mean(scales)),
        center_x=center_x,
        center_y=center_y,
        rotation_deg=rotation,
        transform=tuple(
            name
            for name, applied in (
                ("transpose", transpose),
                ("flip_rows", flip_rows),
                ("flip_columns", flip_columns),
            )
            if applied
        ),
        _wcs=wcs,
        _transpose=transpose,
        _flip_rows=flip_rows,
        _flip_columns=flip_columns,
        _source_shape=shape,
    )


def _orientation(
    wcs: WCS,
    ra: float,
    dec: float,
) -> tuple[bool, bool, bool, float]:
    """Transpose/flips giving north up and east left, plus residual rotation.

    Uses finite differences of the WCS at the centre: east/north offsets
    (arcsec) per +1 pixel in x (column) and y (row).
    """
    x0, y0 = (float(v) for v in wcs.world_to_pixel_values(ra, dec))
    ra0, dec0 = (float(v) for v in wcs.pixel_to_world_values(x0, y0))
    cos_dec = math.cos(math.radians(dec0))

    def offsets(dx: float, dy: float) -> tuple[float, float]:
        ra1, dec1 = (float(v) for v in wcs.pixel_to_world_values(x0 + dx, y0 + dy))
        delta_ra = (ra1 - ra0 + 180.0) % 360.0 - 180.0
        return delta_ra * cos_dec, dec1 - dec0

    east_x, north_x = offsets(1.0, 0.0)
    east_y, north_y = offsets(0.0, 1.0)
    transpose = abs(east_x) + abs(north_y) < abs(east_y) + abs(north_x)
    if transpose:
        # After transposing, columns follow the old y axis and rows the old x.
        east_column, north_row = east_y, north_x
    else:
        east_column, north_row = east_x, north_y
    flip_columns = east_column > 0  # east must decrease to the right
    flip_rows = north_row > 0  # north must decrease downwards

    # Angle of north relative to display-up after the flips (0 = aligned).
    north_column = north_y if transpose else north_x
    north_row_signed = -north_row if flip_rows else north_row
    north_column_signed = -north_column if flip_columns else north_column
    rotation = math.degrees(math.atan2(north_column_signed, -north_row_signed))
    return transpose, flip_rows, flip_columns, rotation


def _to_display(
    x: float,
    y: float,
    shape: tuple[int, int],
    transpose: bool,
    flip_rows: bool,
    flip_columns: bool,
) -> tuple[float, float]:
    """Map FITS array (x=column, y=row, 0-based) to display (column, row)."""
    rows, columns = shape
    column, row = x, y
    if transpose:
        column, row = y, x
        rows, columns = columns, rows
    if flip_rows:
        row = rows - 1 - row
    if flip_columns:
        column = columns - 1 - column
    return column, row

import astropy
import httpx
import numpy
import pandas


def test_science_dependencies_are_importable() -> None:
    assert astropy.__name__ == "astropy"
    assert httpx.__name__ == "httpx"
    assert numpy.__name__ == "numpy"
    assert pandas.__name__ == "pandas"

"""
MODULUS Wearable — Data ingestion
=================================

A small abstraction over "where the sensor data comes from":

- :class:`DataSource` — the abstract interface scoring code depends on.
- :class:`FitFileSource` — parses Garmin ``.FIT`` files (the primary,
  offline, credential-free path for a Fenix 5 Plus owner).
- :class:`SyntheticSource` — deterministic generator for tests and demos.
"""

from src.wearable.ingestion.base import DataSource
from src.wearable.ingestion.synthetic import SyntheticSource
from src.wearable.ingestion.fit_parser import FitFileSource, FIT_AVAILABLE

__all__ = ["DataSource", "SyntheticSource", "FitFileSource", "FIT_AVAILABLE"]

from __future__ import annotations

from dataclasses import dataclass, field
import math
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Callable

from backend.parseFilters import SearchFilters


@dataclass(frozen=True)
class Airport:
    iata_code: str
    name: str
    iso_country: str
    iso_region: str
    airport_type: str
    latitude: float
    longitude: float

@dataclass(frozen=True)
class RankedAirport:
    airport: Airport
    scores: Dict[str, float]
    percent_match: float


@dataclass(frozen=True)
class RankResult:
    ranked: List[RankedAirport]
    active_score_keys: List[str]
    diagnostics: Dict[str, object] = field(default_factory=dict)



from __future__ import annotations

# ============================
# ======== IMPORTS ===========
# ============================

from dataclasses import dataclass, field
import math
import sqlite3
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Callable

from parseResults import (
    FlightResult, 
    FlightEndpoint, 
    AirlineInfo, 
    FlightInfo,
    load_results_json,
    parse_results_json
)
from parseFilters import (
    SearchFilters, 
    load_filters_json, 
    parse_filters_json
)
from airportFiltering import (
    RankedAirport,
    import_airport_data,
    initialize_ranked_airports,
    overall_rank,
    run_all_ranks,
)


# ================================
# ======== DATA MODELS ===========
# ================================




# ====================================
# ======== SCORING CONSTANTS =========
# ====================================


# ============================
# ======== HELPERS ===========
# ============================


# ======================================
# ======== RANKING FUNCTIONS ===========
# ======================================


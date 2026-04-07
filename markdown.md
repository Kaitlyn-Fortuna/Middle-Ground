# Pseudocode Test Cases

These are assignment-style pseudocode test cases for the main functions in the travel-ranking flow:

- Parsing filters
- Airport autofill
- Ranking airports
- Ranking flights
- Combining airport and flight results
- Getting flight data from the external API

## Parsing Filters

### Function: `parse_filters_api_json(payload)`

This function is the main entry point for turning API request data into a `SearchFilters` object. It accepts either a dictionary, a JSON string, or `null`, and returns a clean filter object that the rest of the ranking pipeline can use. If the payload is missing, invalid JSON, or not a dictionary after parsing, it does not crash. Instead, it safely returns an empty `SearchFilters` object.

```text
TEST "parse_filters_api_json - JSON String Payload - Normalized Search Filters"
    Payload = JSON string:
        {
            "departureDate": "2026-04-08",
            "returnDate": "2026-04-16",
            "airports": [" dtw ", "lga", "DTW"],
            "weather": [" Hot ", "Warm"],
            "conditions": ["Sunny"],
            "geography": ["Urban"],
            "maxFlightTime": "6",
            "maxFlightCost": "500"
        }
    ExpectedResult = SearchFilters with:
        departure_date = "2026-04-08"
        return_date = "2026-04-16"
        airports = ["DTW", "LGA"]
        weather_preferences = ["hot", "warm"]
        conditions_preferences = ["sunny"]
        geography_preferences = ["urban"]
        max_flight_time = 6
        max_flight_cost = 500

    ActualResult = parse_filters_api_json(Payload)

    ASSERT ActualResult EQUALS ExpectedResult
END TEST
```

## Airport Autofill

### Function: `makeAirportRecord(raw)`

This function converts a raw airport row into a normalized airport record that is easier to search from the UI. It uppercases the IATA code, trims text fields, and builds extra searchable strings for fuzzy matching by airport name, city, and region. It does not throw errors for incomplete data by itself, but if important values are missing, the resulting record may later be filtered out by the catalog-loading step.

```text
TEST "makeAirportRecord - Valid Airport Row - Searchable Airport Record"
    RawAirport = {
        "iata_code": " dtw ",
        "name": "Detroit Metropolitan Wayne County Airport",
        "municipality": "Detroit",
        "iso_region": "US-MI"
    }
    ExpectedResult = AirportRecord with:
        iata_code = "DTW"
        name = "Detroit Metropolitan Wayne County Airport"
        municipality = "Detroit"
        iso_region = "US-MI"
        search_name = normalized airport name
        search_city = normalized city
        search_all = normalized combined search text
        compact_all = combined text without spaces

    ActualResult = makeAirportRecord(RawAirport)

    ASSERT ActualResult EQUALS ExpectedResult
END TEST
```

## Ranking Airports

### Function: `run_all_ranks(airports, filters)`

This function runs the full airport-scoring pipeline across all active airport-related filters. It applies the individual ranking steps for temperature, sun, rain, humidity, coastal distance, beach distance, urban population, and mountainous terrain, then returns the same airport list with score data added. It does not directly throw user-facing errors for missing filter categories; if no category is active, those score sections are simply skipped.

```text
TEST "run_all_ranks - Weather And Geography Filters - Airport Scores Added"
    Airports = [AirportA, AirportB, AirportC]
    Filters = SearchFilters with:
        weather_preferences = ["hot"]
        conditions_preferences = ["sunny"]
        geography_preferences = ["urban"]

    ActualResult = run_all_ranks(Airports, Filters)

    ASSERT each airport in ActualResult HAS score keys for active filters
END TEST
```

### Function: `overall_rank(airports, filters)`

This function takes the individual airport scores and turns them into one overall airport ranking. It averages the active score values for each airport, stores that average as `percent_match`, and sorts airports from best match to worst match. If an airport has no active scores, its percent match stays empty instead of causing a divide-by-zero error.

```text
TEST "overall_rank - Multiple Airport Scores - Average Percent Match And Sort Descending"
    Airports = [
        RankedAirport1 with scores: {temperature: 0.9, sunny: 0.8},
        RankedAirport2 with scores: {temperature: 0.6, sunny: 0.7},
        RankedAirport3 with scores: {temperature: 1.0, sunny: 0.95}
    ]
    Filters = SearchFilters with active airport filters
    ExpectedOrder = [RankedAirport3, RankedAirport1, RankedAirport2]

    ActualResult = overall_rank(Airports, Filters)

    ASSERT ActualResult.ranked IS IN ExpectedOrder
    ASSERT ActualResult.ranked[0].percent_match EQUALS average of its active scores
    ASSERT ActualResult.active_score_keys CONTAINS ["temperature", "sunny"]
END TEST
```

## Ranking Flights

### Function: `_score_flight(flight, filters)`

This function scores one flight against the active flight-related filters, mainly flight time, estimated cost, and departure-date alignment. Its result is a dictionary with the normalized flight details, individual score parts, and one combined percent-match value. If no flight filters are active, it treats the flight as fully valid and returns a default `percent_match` of `1.0` instead of failing.

```text
TEST "_score_flight - Flight Matches Time Cost And Date - High Percent Match"
    Flight = Flight from DTW to PHX on "2026-04-08" with valid duration and schedule
    Filters = SearchFilters with:
        departure_date = "2026-04-08"
        max_flight_time = 6
        max_flight_cost = 500

    ActualResult = _score_flight(Flight, Filters)

    ASSERT ActualResult.scores CONTAINS "flight_time"
    ASSERT ActualResult.scores CONTAINS "flight_cost"
    ASSERT ActualResult.scores CONTAINS "departure_date"
    ASSERT ActualResult.percent_match IS BETWEEN 0.0 AND 1.0
END TEST
```

### Function: `_rank_route_flights(route_flights, filters)`

This function compares all available flight options for a single route and ranks them from best to worst. It first scores each option, then sorts them by percent match, with flight duration and cost used as tie-breakers, and finally assigns a rank number to each one. If the route has no valid flights, it simply returns an empty list.

```text
TEST "_rank_route_flights - Multiple Flight Options - Best Flight Ranked First"
    RouteFlights = [FlightOption1, FlightOption2, FlightOption3]
    Filters = SearchFilters with:
        max_flight_time = 5
        max_flight_cost = 450
        departure_date = "2026-04-08"

    ActualResult = _rank_route_flights(RouteFlights, Filters)

    ASSERT ActualResult[0].rank EQUALS 1
    ASSERT ActualResult[1].rank EQUALS 2
    ASSERT ActualResult[2].rank EQUALS 3
    ASSERT ActualResult IS SORTED by best percent_match first
END TEST
```

## Combining Airport And Flight Results

### Function: `build_combined_destination_rankings(airport_ranked, filters, api_key)`

This function is the main “optimize travel” pipeline. It starts with the already-ranked destination airports, checks live flight availability from each selected origin airport, scores those flights, and then combines the airport score and flight score into one destination result. It raises an error if required trip inputs are missing, skips destinations that do not have flights from every selected origin, and keeps moving down the airport ranking until it finds enough destinations with valid flight data.

```text
TEST "build_combined_destination_rankings - Shared Flights Found - Airport And Flight Scores Combined"
    RankedAirports = [DestinationA, DestinationB]
    Filters = SearchFilters with:
        airports = ["DTW", "LAX"]
        departure_date = "2026-04-08"
        return_date = "2026-04-16"
        max_flight_time = 6
        max_flight_cost = 500
    ApiKey = "test-key"
    MockRouteData = {
        DTW -> DestinationA = [FlightA1, FlightA2],
        LAX -> DestinationA = [FlightA3],
        DTW -> DestinationB = [FlightB1],
        LAX -> DestinationB = [FlightB2]
    }

    ActualResult = build_combined_destination_rankings(RankedAirports, Filters, ApiKey)

    ASSERT each destination in ActualResult.results HAS:
        airport_rank
        airport_score
        flight_score
        combined_score
        combined_price_usd
        flights
    ASSERT flights inside each destination are kept in alphabetical origin order
END TEST
```

## Getting Flight Data From The External API

### Function: `fetch_route_payload(origin_iata, destination_iata, departure_date)`

This function sends the route-level request to the external FlightAPI and returns the raw response payload for one origin, one destination, and one departure date. It also uses the local cache so repeated requests for the same route do not waste API credits. If the API returns “no data,” it stores an empty result in cache, and if the request fails in a way the app considers fatal, it raises a flight API error for the caller to handle.

```text
TEST "fetch_route_payload - Valid Route Request - Returns Cached Or Live Route Payload"
    Origin = "DTW"
    Destination = "PHX"
    DepartureDate = "2026-04-08"
    ApiKey = "valid-key"

    ActualResult = fetch_route_payload(Origin, Destination, DepartureDate)

    ASSERT ActualResult IS NOT null
    ASSERT diagnostics.route_pairs_requested CONTAINS requested route
END TEST
```

### Function: `load_route_flights(origin_iata, destination_iata, departure_date)`

This function takes the raw route payload from the external API and converts the usable flight rows into normalized internal `Flight` objects. Its result is the clean flight list the ranking code uses later for scoring, sorting, and display. If the payload contains bad rows, missing fields, or non-flight items, those entries are skipped so the valid flights can still be used.

```text
TEST "load_route_flights - Route Payload Contains Flights Array - Flights Are Normalized"
    Origin = "DTW"
    Destination = "SYR"
    DepartureDate = "2026-04-08"
    MockRoutePayload = {
        "departureAirport": {...},
        "arrivalAirport": {...},
        "flights": [
            FlightRow1,
            FlightRow2
        ]
    }

    ActualResult = load_route_flights(Origin, Destination, DepartureDate)

    ASSERT LENGTH(ActualResult) EQUALS 2
    ASSERT ActualResult[0] IS A normalized Flight object
    ASSERT ActualResult[0].departure_iata EQUALS "DTW"
    ASSERT ActualResult[0].arrival_iata EQUALS "SYR"
END TEST
```

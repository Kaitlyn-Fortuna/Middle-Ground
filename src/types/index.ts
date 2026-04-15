export interface AirportOption {
  iata_code: string
  name: string
  municipality: string
  iso_region: string
}

export interface AirportResponse {
  status?: string
  message?: string
  results?: AirportOption[]
}

export interface FlightResultRow {
  airline_iata?: string | null
  airline_name?: string | null
  arrival_iata?: string | null
  arrival_scheduled?: string | null
  departure_iata?: string | null
  departure_scheduled?: string | null
  duration_hours?: number | null
  estimated_cost_usd?: number | null
  flight_callsign?: string | null
  flight_date?: string | null
  flight_iata?: string | null
  flight_number?: string | null
  flight_rank?: number | null
  flight_status?: string | null
  option_count?: number | null
  origin_slot?: number | null
  percent_match?: number | null
  rank?: number | null
  scores?: Record<string, number>
}

export interface AirportBreakdownRow {
  actual?: string | null
  key?: string
  label?: string
  score?: number | null
  target?: string | null
}

export interface DestinationResultRow {
  airport_breakdown?: AirportBreakdownRow[]
  airport_rank?: number | null
  airport_score?: number | null
  combined_price_usd?: number | null
  combined_score?: number | null
  destination_iata?: string | null
  destination_name?: string | null
  flight_rank?: number | null
  flight_score?: number | null
  flights?: FlightResultRow[]
  rank?: number | null
}

export interface RankDiagnostics {
  selected_origin_airports?: string[]
  flight_filter_context?: {
    departure_date?: string | null
    max_flight_cost?: number | null
    max_flight_time?: number | null
    return_date?: string | null
  }
  live_flights_loaded?: number
  candidate_destinations_considered?: string[]
  route_errors?: Array<Record<string, string>>
}

export interface RankCombinedResponse {
  status?: string
  message?: string | null
  error?: string | null
  count?: number
  results?: DestinationResultRow[]
  diagnostics?: RankDiagnostics
  active_score_keys?: {
    airport?: string[]
    flight?: string[]
  }
}

export interface GroupMemberHandle {
  focusInput: () => void
}

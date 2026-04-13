<script setup lang="ts">
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { RangeCalendar } from '@/components/ui/range-calendar'
import { Slider } from '@/components/ui/slider'
import GroupMember from '@/components/GroupMember.vue'
import PreferenceButton from '@/components/PreferenceButton.vue'
import {
  Building2,
  CloudRain,
  DropletOff,
  Droplets,
  LoaderCircle,
  Mountain,
  Plane,
  Plus,
  Snowflake,
  Sun,
  SunDim,
  Thermometer,
  TreePalm,
  Waves,
  Wind,
} from 'lucide-vue-next'
import { getLocalTimeZone, today } from '@internationalized/date'
import type { DateRange } from 'reka-ui'
import { computed, onMounted, onUnmounted, ref, type Ref, watch } from 'vue'

interface AirportOption {
  iata_code: string
  name: string
  municipality: string
  iso_region: string
}

interface AirportResponse {
  status?: string
  message?: string
  results?: AirportOption[]
}

interface FlightResultRow {
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

interface AirportBreakdownRow {
  actual?: string | null
  key?: string
  label?: string
  score?: number | null
  target?: string | null
}

interface DestinationResultRow {
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

interface RankDiagnostics {
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

interface RankCombinedResponse {
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

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5001/api').replace(/\/$/, '')
const RESULTS_LIMIT = 10

const groupMembers = ref<string[][]>([])

const start = today(getLocalTimeZone())
const end = start.add({ days: 30 })
const dateRange = ref({
  start,
  end,
}) as Ref<DateRange>

const hotPreference = ref(false)
const warmPreference = ref(false)
const mildPreference = ref(false)
const coolPreference = ref(false)
const coldPreference = ref(false)

const sunnyPreference = ref(false)
const aridPreference = ref(false)
const rainyPreference = ref(false)
const dryPreference = ref(false)
const humidPreference = ref(false)

const beachPreference = ref(false)
const coastalPreference = ref(false)
const urbanPreference = ref(false)
const mountainPreference = ref(false)

const budget = ref([500])
const maxFlightTime = ref([6])

const phase = ref<'setup' | 'searching' | 'done'>('setup')
const airportOptions = ref<AirportOption[]>([])
const airportLoadError = ref<string | null>(null)
const isAirportsLoading = ref(false)
const searchError = ref<string | null>(null)
const searchMessage = ref<string | null>(null)
const resultRows = ref<DestinationResultRow[]>([])
const resultDiagnostics = ref<RankDiagnostics | null>(null)
const activeScoreKeys = ref<{ airport: string[]; flight: string[] }>({ airport: [], flight: [] })
const loadingMessages = [
  {
    title: 'Optimizing your trip...',
    detail: 'Balancing destination fit with practical flights for the whole group.',
  },
  {
    title: 'Checking shared destinations...',
    detail: 'Making sure every traveler can reach the same airport.',
  },
  {
    title: 'Comparing routes and costs...',
    detail: 'Sorting through the best options for time, price, and date match.',
  },
  {
    title: 'Finding the middle ground...',
    detail: 'Pulling together the destinations that make the most sense for everyone.',
  },
] as const
const loadingMessageIndex = ref(0)
let loadingMessageTimer: ReturnType<typeof setInterval> | null = null

const selectedOriginAirports = computed(() =>
  groupMembers.value.map((member) => member[0]?.trim().toUpperCase()).filter(Boolean) as string[],
)

const requestBody = computed(() => ({
  departure_date: dateRange.value?.start?.toString() || '',
  return_date: dateRange.value?.end?.toString() || '',
  airports: selectedOriginAirports.value,
  weather_preferences: [
    ...(hotPreference.value ? ['hot'] : []),
    ...(warmPreference.value ? ['warm'] : []),
    ...(mildPreference.value ? ['mild'] : []),
    ...(coolPreference.value ? ['cool'] : []),
    ...(coldPreference.value ? ['cold'] : []),
  ],
  conditions_preferences: [
    ...(sunnyPreference.value ? ['sunny'] : []),
    ...(aridPreference.value ? ['dry'] : []),
    ...(rainyPreference.value ? ['wet'] : []),
    ...(dryPreference.value ? ['low humidity'] : []),
    ...(humidPreference.value ? ['high humidity'] : []),
  ],
  geography_preferences: [
    ...(beachPreference.value ? ['beach'] : []),
    ...(coastalPreference.value ? ['coastal'] : []),
    ...(urbanPreference.value ? ['urban'] : []),
    ...(mountainPreference.value ? ['mountainous'] : []),
  ],
  max_flight_cost: budget.value[0],
  max_flight_time: maxFlightTime.value[0],
  max_connections: 1,
  prefer_nonstop: true,
  domestic_only: true,
}))

const isSearchReady = computed(
  () =>
    groupMembers.value.length >= 2 &&
    groupMembers.value.every((member) => Boolean(member[0])) &&
    !isAirportsLoading.value,
)

const responseOrigins = computed(
  () => resultDiagnostics.value?.selected_origin_airports || selectedOriginAirports.value,
)

const summaryMessage = computed(() => {
  if (searchError.value) return searchError.value
  if (searchMessage.value) return searchMessage.value
  if (resultRows.value.length === 0) return "There isn't an airport that has all selected origin airports in common."
  return null
})

const currentLoadingMessage = computed(
  () => loadingMessages[loadingMessageIndex.value % loadingMessages.length] ?? loadingMessages[0],
)

function scoreBadgeClass(score?: number | null): string {
  if (score == null) return 'bg-slate-500/10 text-slate-700 ring-1 ring-slate-300/70'
  if (score >= 0.9) return 'bg-emerald-500/14 text-emerald-950 ring-1 ring-emerald-400/25'
  if (score >= 0.75) return 'bg-sky-500/14 text-sky-950 ring-1 ring-sky-400/25'
  if (score >= 0.6) return 'bg-amber-500/16 text-amber-950 ring-1 ring-amber-400/25'
  return 'bg-rose-500/14 text-rose-950 ring-1 ring-rose-400/25'
}

function scoreSurfaceClass(score?: number | null): string {
  if (score == null) return 'border-white/70 bg-white/72'
  if (score >= 0.9) return 'border-emerald-200/70 bg-emerald-50/45'
  if (score >= 0.75) return 'border-sky-200/70 bg-sky-50/45'
  if (score >= 0.6) return 'border-amber-200/70 bg-amber-50/45'
  return 'border-rose-200/70 bg-rose-50/45'
}

function formatPercent(score?: number | null): string {
  if (score == null || Number.isNaN(score)) return 'N/A'
  return `${Math.round(score * 100)}%`
}

function formatMoney(value?: number | null): string {
  if (value == null || Number.isNaN(value)) return 'N/A'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value)
}

function formatDateTime(value?: string | null): string {
  if (!value) return 'N/A'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleString()
}

function formatDuration(hours?: number | null): string {
  if (hours == null || Number.isNaN(hours)) return 'N/A'
  const totalMinutes = Math.round(hours * 60)
  const wholeHours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60

  if (wholeHours <= 0) return `${minutes} min`
  if (minutes === 0) return `${wholeHours} hr`
  return `${wholeHours} hr ${minutes} min`
}

function resetLoadingMessages() {
  loadingMessageIndex.value = 0
  if (loadingMessageTimer) {
    clearInterval(loadingMessageTimer)
    loadingMessageTimer = null
  }
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init)
  const rawBody = await response.text()
  let data: unknown = {}

  try {
    data = rawBody ? JSON.parse(rawBody) : {}
  } catch {
    data = { message: rawBody || `Request failed (${response.status})` }
  }

  if (!response.ok) {
    const message =
      typeof data === 'object' && data !== null
        ? String(
            (data as { message?: string; error?: string }).message ||
              (data as { message?: string; error?: string }).error ||
              `Request failed (${response.status})`,
          )
        : `Request failed (${response.status})`
    throw new Error(message)
  }

  return data as T
}

async function loadAirports() {
  isAirportsLoading.value = true
  airportLoadError.value = null

  try {
    const payload = await apiRequest<AirportResponse>('/airports')
    airportOptions.value = Array.isArray(payload.results) ? payload.results : []
  } catch (error) {
    airportLoadError.value = error instanceof Error ? error.message : 'Unable to load airports.'
    airportOptions.value = []
  } finally {
    isAirportsLoading.value = false
  }
}

async function search() {
  if (!isSearchReady.value) return

  phase.value = 'searching'
  searchError.value = null
  searchMessage.value = null
  resultRows.value = []
  resultDiagnostics.value = null
  activeScoreKeys.value = { airport: [], flight: [] }

  try {
    const payload = await apiRequest<RankCombinedResponse>(`/rank-combined?limit=${RESULTS_LIMIT}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody.value),
    })

    resultRows.value = Array.isArray(payload.results) ? payload.results : []
    resultDiagnostics.value = payload.diagnostics || null
    activeScoreKeys.value = {
      airport: payload.active_score_keys?.airport || [],
      flight: payload.active_score_keys?.flight || [],
    }
    searchMessage.value = payload.message || null
  } catch (error) {
    searchError.value = error instanceof Error ? error.message : 'Unable to optimize travel.'
  } finally {
    phase.value = 'done'
  }
}

function editSearch() {
  phase.value = 'setup'
}

onMounted(() => {
  void loadAirports()
})

watch(phase, (value) => {
  if (value === 'searching') {
    resetLoadingMessages()
    loadingMessageTimer = setInterval(() => {
      loadingMessageIndex.value = (loadingMessageIndex.value + 1) % loadingMessages.length
    }, 5000)
    return
  }

  resetLoadingMessages()
})

onUnmounted(() => {
  resetLoadingMessages()
})
</script>

<template>
  <div class="min-h-screen bg-slate-100">
    <Transition mode="out-in">
      <div
        v-if="phase === 'setup'"
        class="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-5 py-5 lg:px-6 lg:py-6 xl:h-screen xl:overflow-hidden"
      >
        <div class="mb-5">
          <p class="text-xs font-semibold uppercase tracking-[0.28em] text-sky-700">Middle Ground</p>
          <h1 class="mt-2 text-3xl font-semibold tracking-tight text-slate-900 lg:text-[2rem]">
            Plan a destination everyone can actually reach.
          </h1>
          <p class="mt-2 max-w-3xl text-sm text-slate-600 lg:text-base">
            Pick one home airport per traveler, choose the kind of trip your group wants, and we'll compare the
            best shared destinations for everyone.
          </p>
        </div>

        <Alert v-if="airportLoadError" variant="destructive" class="mb-6">
          <AlertTitle>Airport list unavailable</AlertTitle>
          <AlertDescription class="flex items-center justify-between gap-4">
            <span>{{ airportLoadError }}</span>
            <Button variant="outline" size="sm" class="cursor-pointer" @click="loadAirports">
              Retry
            </Button>
          </AlertDescription>
        </Alert>

        <div class="grid flex-1 min-h-0 gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
          <Card class="self-start border-white/70 bg-white/72 shadow-lg backdrop-blur-md">
            <CardHeader>
              <CardTitle>Group Members</CardTitle>
              <CardDescription>Pick the airport each person would realistically depart from.</CardDescription>
            </CardHeader>
            <CardContent class="space-y-3">
              <div class="max-h-64 space-y-3 overflow-auto rounded-xl bg-slate-50/80 p-3">
                <div v-if="groupMembers.length === 0" class="rounded-lg border border-dashed border-slate-300 p-4 text-sm text-slate-500">
                  No group members added yet.
                </div>
                <GroupMember
                  v-for="(member, index) in groupMembers"
                  :key="index"
                  v-model:airports="groupMembers[index]"
                  :airport-options="airportOptions"
                  :loading-airports="isAirportsLoading"
                  :delete-member="() => groupMembers.splice(index, 1)"
                />
              </div>
              <Button
                class="cursor-pointer"
                size="sm"
                variant="outline"
                @click="groupMembers.push([])"
              >
                <Plus class="mr-1 h-4 w-4" />
                Add Group Member
              </Button>
              <p class="text-xs text-slate-500">
                Tip: two or more travelers makes the results much more useful.
              </p>
            </CardContent>
          </Card>

          <Card class="border-white/70 bg-white/72 shadow-lg backdrop-blur-md">
            <CardHeader>
              <CardTitle>Preferences</CardTitle>
              <CardDescription>Set the trip window and the kind of destination your group would enjoy most.</CardDescription>
            </CardHeader>
            <CardContent class="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
              <section class="space-y-2 xl:col-span-3">
                <h2 class="text-sm font-semibold uppercase tracking-wide text-slate-600">Dates</h2>
                <div class="rounded-xl bg-slate-50/80 p-3">
                  <p class="mb-2 text-xs text-slate-500">Choose the travel window your group can actually make work.</p>
                  <Popover>
                    <PopoverTrigger>
                      <Button variant="outline" class="cursor-pointer">
                        {{ dateRange?.start?.toDate(getLocalTimeZone()).toLocaleDateString() ?? '?' }}
                        -
                        {{ dateRange?.end?.toDate(getLocalTimeZone()).toLocaleDateString() ?? '?' }}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent class="w-auto p-0">
                      <RangeCalendar
                        :number-of-months="2"
                        v-model="dateRange"
                        disable-days-outside-current-view
                      />
                    </PopoverContent>
                  </Popover>
                </div>
              </section>

              <section class="space-y-3">
                <h2 class="text-sm font-semibold uppercase tracking-wide text-slate-600">Weather</h2>
                <div class="rounded-xl bg-slate-50/80 p-3">
                  <h3 class="mb-2 text-sm font-medium text-slate-700">Temperature</h3>
                  <div class="grid grid-cols-2 gap-2 sm:grid-cols-5">
                    <PreferenceButton :icon="Sun" v-model="hotPreference">Hot</PreferenceButton>
                    <PreferenceButton :icon="SunDim" v-model="warmPreference">Warm</PreferenceButton>
                    <PreferenceButton :icon="Thermometer" v-model="mildPreference">Mild</PreferenceButton>
                    <PreferenceButton :icon="Wind" v-model="coolPreference">Cool</PreferenceButton>
                    <PreferenceButton :icon="Snowflake" v-model="coldPreference">Cold</PreferenceButton>
                  </div>
                </div>
                <div class="rounded-xl bg-slate-50/80 p-3">
                  <h3 class="mb-2 text-sm font-medium text-slate-700">Conditions</h3>
                  <div class="grid grid-cols-2 gap-2 sm:grid-cols-5">
                    <PreferenceButton :icon="Sun" v-model="sunnyPreference">Sunny</PreferenceButton>
                    <PreferenceButton :icon="SunDim" v-model="aridPreference">Arid</PreferenceButton>
                    <PreferenceButton :icon="CloudRain" v-model="rainyPreference">Rainy</PreferenceButton>
                    <PreferenceButton :icon="DropletOff" v-model="dryPreference">Dry</PreferenceButton>
                    <PreferenceButton :icon="Droplets" v-model="humidPreference">Humid</PreferenceButton>
                  </div>
                </div>
              </section>

              <section class="space-y-3">
                <h2 class="text-sm font-semibold uppercase tracking-wide text-slate-600">Geography</h2>
                <div class="rounded-xl bg-slate-50/80 p-3">
                  <p class="mb-2 text-xs text-slate-500">Tell the app what kind of place would feel right for the group.</p>
                  <div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
                    <PreferenceButton :icon="TreePalm" v-model="beachPreference">Beach</PreferenceButton>
                    <PreferenceButton :icon="Waves" v-model="coastalPreference">Coastal</PreferenceButton>
                    <PreferenceButton :icon="Building2" v-model="urbanPreference">Urban</PreferenceButton>
                    <PreferenceButton :icon="Mountain" v-model="mountainPreference">
                      Mountains
                    </PreferenceButton>
                  </div>
                </div>
              </section>

              <section class="space-y-3">
                <div>
                  <h2 class="text-sm font-semibold uppercase tracking-wide text-slate-600">Max Flight Cost</h2>
                  <div class="rounded-xl bg-slate-50/80 px-4 py-3">
                    <Slider v-model="budget" :max="1000" :min="100" :step="25" />
                    <p class="mt-2 text-sm text-slate-600">{{ formatMoney(budget[0]) }} per traveler</p>
                    <p class="mt-1 text-xs text-slate-500">This helps keep pricier flight options from floating to the top.</p>
                  </div>
                </div>
                <div>
                  <h2 class="text-sm font-semibold uppercase tracking-wide text-slate-600">Max Flight Time</h2>
                  <div class="rounded-xl bg-slate-50/80 px-4 py-3">
                    <Slider v-model="maxFlightTime" :max="16" :min="2" :step="1" />
                    <p class="mt-2 text-sm text-slate-600">{{ maxFlightTime[0] }} hours</p>
                    <p class="mt-1 text-xs text-slate-500">Shorter limits favor destinations that are easier on the whole group.</p>
                  </div>
                </div>
              </section>
            </CardContent>
          </Card>
        </div>

        <div class="mt-5 flex flex-col items-center gap-2">
          <Button :disabled="!isSearchReady" class="cursor-pointer px-6" @click="search">
            <Plane class="mr-2 h-4 w-4" />
            Search Shared Destinations
          </Button>
          <p class="text-sm text-slate-500">
            {{
              isSearchReady
                ? 'Ready to search the backend.'
                : 'Add at least two travelers and select one airport for each to start.'
            }}
          </p>
        </div>
      </div>

      <div
        v-else-if="phase === 'searching'"
        class="flex min-h-screen flex-col items-center justify-center gap-4 text-slate-700"
      >
        <div class="rounded-3xl border border-white/70 bg-white/70 px-8 py-10 text-center shadow-xl backdrop-blur-md">
          <LoaderCircle class="mx-auto h-11 w-11 animate-spin text-sky-700" />
          <h1 class="mt-5 text-3xl font-semibold text-slate-900">{{ currentLoadingMessage.title }}</h1>
          <p class="mt-3 max-w-md text-base text-slate-600">{{ currentLoadingMessage.detail }}</p>
        </div>
      </div>

      <div v-else class="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-5 py-6 lg:px-6">
        <div class="mb-6 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <p class="text-xs font-semibold uppercase tracking-[0.28em] text-sky-700">Results</p>
            <h1 class="mt-2 text-3xl font-semibold tracking-tight text-slate-900 lg:text-[2rem]">
              {{ resultRows.length ? `Found ${resultRows.length} shared destinations` : 'No shared destinations found' }}
            </h1>
            <p class="mt-2 max-w-3xl text-sm text-slate-600 lg:text-base">
              Origins:
              <strong>{{ responseOrigins.join(', ') || 'N/A' }}</strong>
              <span class="mx-2 text-slate-300">|</span>
              Dates:
              <strong>{{ requestBody.departure_date }}</strong>
              to
              <strong>{{ requestBody.return_date }}</strong>
            </p>
          </div>
          <Button variant="outline" class="cursor-pointer self-start" @click="editSearch">
            Edit Search
          </Button>
        </div>

        <Alert v-if="summaryMessage" :variant="searchError ? 'destructive' : 'default'" class="mb-6">
          <AlertTitle>{{ searchError ? 'Search failed' : 'Search note' }}</AlertTitle>
          <AlertDescription>{{ summaryMessage }}</AlertDescription>
        </Alert>

        <div v-if="resultRows.length" class="mb-6 space-y-4">
          <Card class="border-white/70 bg-white/74 shadow-lg backdrop-blur-md">
            <CardHeader>
              <CardTitle class="text-base">Backend Summary</CardTitle>
            </CardHeader>
            <CardContent class="flex flex-wrap gap-3 text-sm text-slate-700">
              <span class="rounded-full bg-slate-100/85 px-3 py-1">Live flights loaded: {{ resultDiagnostics?.live_flights_loaded ?? 'N/A' }}</span>
              <span class="rounded-full bg-slate-100/85 px-3 py-1">
                Candidate destinations considered: {{ resultDiagnostics?.candidate_destinations_considered?.length ?? 0 }}
              </span>
              <span class="rounded-full bg-slate-100/85 px-3 py-1">
                Airport score keys: {{ activeScoreKeys.airport.join(', ') || 'None' }}
              </span>
              <span class="rounded-full bg-slate-100/85 px-3 py-1">
                Flight score keys: {{ activeScoreKeys.flight.join(', ') || 'None' }}
              </span>
            </CardContent>
          </Card>
          <Card
            v-if="resultDiagnostics?.route_errors?.length"
            class="border-amber-200/70 bg-amber-50/70 shadow-lg backdrop-blur-md"
          >
            <CardHeader>
              <CardTitle class="text-base">Route Warnings</CardTitle>
              <CardDescription>Some origin/destination lookups returned provider errors.</CardDescription>
            </CardHeader>
            <CardContent class="space-y-2 text-sm text-amber-900">
              <p
                v-for="(routeError, index) in resultDiagnostics.route_errors"
                :key="`${routeError.origin_iata}-${routeError.destination_iata}-${index}`"
              >
                {{ routeError.origin_iata }} → {{ routeError.destination_iata }}: {{ routeError.error }}
              </p>
            </CardContent>
          </Card>
        </div>

        <div v-if="resultRows.length" class="space-y-5">
          <Card
            v-for="destination in resultRows"
            :key="`${destination.destination_iata}-${destination.rank}`"
            class="border-white/70 shadow-xl backdrop-blur-md"
            :class="scoreSurfaceClass(destination.combined_score)"
          >
            <CardHeader class="gap-3">
              <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div>
                  <p class="text-xs font-semibold uppercase tracking-[0.24em] text-sky-700">
                    Rank #{{ destination.rank ?? 'N/A' }}
                  </p>
                  <CardTitle class="mt-1 text-2xl">
                    {{ destination.destination_iata }}
                    <span class="text-lg font-normal text-slate-500">
                      {{ destination.destination_name ? `- ${destination.destination_name}` : '' }}
                    </span>
                  </CardTitle>
                </div>
                <span
                  class="inline-flex w-fit rounded-full px-3 py-1 text-sm font-semibold"
                  :class="scoreBadgeClass(destination.combined_score)"
                >
                  {{ formatPercent(destination.combined_score) }} match
                </span>
              </div>
              <div class="flex flex-wrap gap-2 text-sm">
                <span class="rounded-full px-3 py-1 text-slate-800 ring-1 ring-black/5 backdrop-blur-sm" :class="scoreBadgeClass(destination.airport_score)">
                  Airport #{{ destination.airport_rank ?? 'N/A' }} · {{ formatPercent(destination.airport_score) }}
                </span>
                <span class="rounded-full px-3 py-1 text-slate-800 ring-1 ring-black/5 backdrop-blur-sm" :class="scoreBadgeClass(destination.flight_score)">
                  Flights #{{ destination.flight_rank ?? 'N/A' }} · {{ formatPercent(destination.flight_score) }}
                </span>
                <span class="rounded-full bg-slate-900/6 px-3 py-1 text-slate-800 ring-1 ring-black/5 backdrop-blur-sm">
                  Group est. {{ formatMoney(destination.combined_price_usd) }}
                </span>
              </div>
            </CardHeader>

            <CardContent class="grid gap-5 xl:grid-cols-[340px_minmax(0,1fr)]">
              <section v-if="destination.airport_breakdown?.length" class="space-y-3">
                <h3 class="text-sm font-semibold uppercase tracking-wide text-slate-600">Airport Breakdown</h3>
                <div class="grid gap-3">
                  <div
                    v-for="metric in destination.airport_breakdown"
                    :key="`${destination.destination_iata}-${metric.key}`"
                    class="rounded-xl border border-white/70 bg-white/62 p-3 shadow-sm backdrop-blur-sm"
                  >
                    <div class="flex items-start justify-between gap-3">
                      <div>
                        <p class="font-medium text-slate-900">{{ metric.label || metric.key }}</p>
                        <p class="mt-1 text-sm text-slate-500">Target: {{ metric.target || 'N/A' }}</p>
                        <p class="text-sm text-slate-500">Actual: {{ metric.actual || 'N/A' }}</p>
                      </div>
                      <span
                        class="inline-flex rounded-full px-2.5 py-1 text-xs font-semibold backdrop-blur-sm"
                        :class="scoreBadgeClass(metric.score)"
                      >
                        {{ formatPercent(metric.score) }}
                      </span>
                    </div>
                  </div>
                </div>
              </section>

              <section class="space-y-3">
                <h3 class="text-sm font-semibold uppercase tracking-wide text-slate-600">Best Flight Per Origin</h3>
                <div class="space-y-3">
                  <div
                    v-for="flight in destination.flights || []"
                    :key="`${destination.destination_iata}-${flight.departure_iata}-${flight.flight_iata}`"
                    class="rounded-2xl border p-4 shadow-sm backdrop-blur-sm"
                    :class="scoreSurfaceClass(flight.percent_match)"
                  >
                    <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div>
                        <p class="text-base font-semibold text-slate-900">
                          {{ flight.departure_iata || 'N/A' }} → {{ flight.arrival_iata || 'N/A' }}
                        </p>
                        <p class="text-sm text-slate-500">
                          {{ flight.airline_name || 'Unknown airline' }}
                          {{ flight.flight_iata ? `· ${flight.flight_iata}` : '' }}
                          {{ flight.flight_status ? `· ${flight.flight_status}` : '' }}
                        </p>
                      </div>
                      <span
                        class="inline-flex w-fit rounded-full px-3 py-1 text-sm font-semibold backdrop-blur-sm"
                        :class="scoreBadgeClass(flight.percent_match)"
                      >
                        {{ formatPercent(flight.percent_match) }}
                      </span>
                    </div>
                    <div class="mt-3 flex flex-wrap gap-2 text-xs text-slate-700">
                      <span class="rounded-full px-2.5 py-1" :class="scoreBadgeClass(flight.scores?.flight_time)">
                        Time {{ formatPercent(flight.scores?.flight_time) }}
                      </span>
                      <span class="rounded-full px-2.5 py-1" :class="scoreBadgeClass(flight.scores?.flight_cost)">
                        Cost {{ formatPercent(flight.scores?.flight_cost) }}
                      </span>
                      <span class="rounded-full px-2.5 py-1" :class="scoreBadgeClass(flight.scores?.departure_date)">
                        Date {{ formatPercent(flight.scores?.departure_date) }}
                      </span>
                    </div>
                    <div class="mt-3 grid gap-2 text-sm text-slate-600 sm:grid-cols-2 lg:grid-cols-3">
                      <p>Depart: {{ formatDateTime(flight.departure_scheduled) }}</p>
                      <p>Arrive: {{ formatDateTime(flight.arrival_scheduled) }}</p>
                      <p>Duration: {{ formatDuration(flight.duration_hours) }}</p>
                      <p>Est. Cost: {{ formatMoney(flight.estimated_cost_usd) }}</p>
                      <p>Options Considered: {{ flight.option_count ?? 'N/A' }}</p>
                      <p>Flight Rank: {{ flight.flight_rank ?? 'N/A' }}</p>
                    </div>
                  </div>
                </div>
              </section>
            </CardContent>
          </Card>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.v-enter-active,
.v-leave-active {
  transition:
    opacity 0.2s ease-out,
    transform 0.2s ease-out;
}

.v-enter-from,
.v-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}
</style>

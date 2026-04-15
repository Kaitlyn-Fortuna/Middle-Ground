<script setup lang="ts">
import { getLocalTimeZone, today } from '@internationalized/date'
import type { DateRange } from 'reka-ui'
import { computed, onMounted, onUnmounted, ref, type Ref, watch } from 'vue'
import SearchSetup from '@/components/SearchSetup.vue'
import SearchLoading from '@/components/SearchLoading.vue'
import SearchResults from '@/components/SearchResults.vue'
import type {
  AirportOption,
  AirportResponse,
  RankCombinedResponse,
  DestinationResultRow,
  RankDiagnostics,
} from '@/types'

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5001/api').replace(
  /\/$/,
  '',
)
const RESULTS_LIMIT = 10

const phase = ref<'setup' | 'searching' | 'done'>('setup')
const groupMembers = ref<string[][]>([])
const start = today(getLocalTimeZone())
const end = start.add({ days: 30 })
const dateRange = ref({
  start,
  end,
}) as Ref<DateRange>

const preferences = ref({
  hot: false,
  warm: false,
  mild: false,
  cool: false,
  cold: false,
  sunny: false,
  arid: false,
  rainy: false,
  dry: false,
  humid: false,
  beach: false,
  coastal: false,
  urban: false,
  mountain: false,
})

const budget = ref([500])
const maxFlightTime = ref([6])

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

const selectedOriginAirports = computed(
  () =>
    groupMembers.value.map((member) => member[0]?.trim().toUpperCase()).filter(Boolean) as string[],
)

const requestBody = computed(() => ({
  departure_date: dateRange.value?.start?.toString() || '',
  return_date: dateRange.value?.end?.toString() || '',
  airports: selectedOriginAirports.value,
  weather_preferences: [
    ...(preferences.value.hot ? ['hot'] : []),
    ...(preferences.value.warm ? ['warm'] : []),
    ...(preferences.value.mild ? ['mild'] : []),
    ...(preferences.value.cool ? ['cool'] : []),
    ...(preferences.value.cold ? ['cold'] : []),
  ],
  conditions_preferences: [
    ...(preferences.value.sunny ? ['sunny'] : []),
    ...(preferences.value.arid ? ['dry'] : []),
    ...(preferences.value.rainy ? ['wet'] : []),
    ...(preferences.value.dry ? ['low humidity'] : []),
    ...(preferences.value.humid ? ['high humidity'] : []),
  ],
  geography_preferences: [
    ...(preferences.value.beach ? ['beach'] : []),
    ...(preferences.value.coastal ? ['coastal'] : []),
    ...(preferences.value.urban ? ['urban'] : []),
    ...(preferences.value.mountain ? ['mountainous'] : []),
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
  if (resultRows.value.length === 0)
    return "There isn't an airport that has all selected origin airports in common."
  return null
})

const currentLoadingMessage = computed(
  () => loadingMessages[loadingMessageIndex.value % loadingMessages.length] ?? loadingMessages[0],
)

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
    const payload = await apiRequest<RankCombinedResponse>(
      `/rank-combined?limit=${RESULTS_LIMIT}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody.value),
      },
    )

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
  <div class="min-h-screen bg-slate-100 overflow-x-hidden">
    <Transition mode="out-in">
      <SearchSetup
        v-if="phase === 'setup'"
        v-model:groupMembers="groupMembers"
        v-model:dateRange="dateRange"
        v-model:budget="budget"
        v-model:maxFlightTime="maxFlightTime"
        v-model:preferences="preferences"
        :airport-options="airportOptions"
        :loading-airports="isAirportsLoading"
        :airport-load-error="airportLoadError"
        :is-search-ready="isSearchReady"
        @search="search"
        @load-airports="loadAirports"
      />

      <SearchLoading
        v-else-if="phase === 'searching'"
        :title="currentLoadingMessage.title"
        :detail="currentLoadingMessage.detail"
      />

      <SearchResults
        v-else
        :result-rows="resultRows"
        :result-diagnostics="resultDiagnostics"
        :response-origins="responseOrigins"
        :departure-date="requestBody.departure_date"
        :return-date="requestBody.return_date"
        :summary-message="summaryMessage"
        :search-error="searchError"
        :active-score-keys="activeScoreKeys"
        @edit-search="editSearch"
      />
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

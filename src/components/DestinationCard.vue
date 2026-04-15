<script setup lang="ts">
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Building2,
  CloudRain,
  DropletOff,
  Droplets,
  Mountain,
  Sun,
  Thermometer,
  TreePalm,
  Waves,
  Trophy,
  Plane,
  Calendar,
  Clock,
  Layers,
  Droplet,
  CloudSun,
  CloudSunRain,
  CircleDollarSign,
} from '@lucide/vue'
import {
  scoreBadgeClass,
  scoreSurfaceClass,
  formatPercent,
  formatMoney,
  formatDateTime,
  formatDuration,
} from '@/lib/formatters'
import type { DestinationResultRow } from '@/types'

defineProps<{
  destination: DestinationResultRow
}>()

const iconMap: Record<string, any> = {
  temperature: Thermometer,
  sunny: Sun,
  dry: CloudSun,
  wet: CloudRain,
  'dry/wet': CloudSunRain,
  'low humidity': DropletOff,
  'high humidity': Droplets,
  'low/high humidity': Droplet,
  beach: TreePalm,
  coastal: Waves,
  urban: Building2,
  mountainous: Mountain,
}
</script>

<template>
  <Card
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
        <span
          class="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-slate-800 ring-1 ring-black/5 backdrop-blur-sm"
          :class="scoreBadgeClass(destination.airport_score)"
        >
          <Building2 class="h-3.5 w-3.5" />
          Airport #{{ destination.airport_rank ?? 'N/A' }} ·
          {{ formatPercent(destination.airport_score) }}
        </span>
        <span
          class="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-slate-800 ring-1 ring-black/5 backdrop-blur-sm"
          :class="scoreBadgeClass(destination.flight_score)"
        >
          <Plane class="h-3.5 w-3.5" />
          Flights #{{ destination.flight_rank ?? 'N/A' }} ·
          {{ formatPercent(destination.flight_score) }}
        </span>
        <span
          class="inline-flex items-center gap-1.5 rounded-full bg-slate-900/6 px-3 py-1 text-slate-800 ring-1 ring-black/5 backdrop-blur-sm"
        >
          <CircleDollarSign class="h-3.5 w-3.5" />
          Group est. {{ formatMoney(destination.combined_price_usd) }}
        </span>
      </div>
    </CardHeader>

    <CardContent class="grid gap-5 xl:grid-cols-[340px_minmax(0,1fr)]">
      <section v-if="destination.airport_breakdown?.length" class="space-y-3">
        <h3 class="text-sm font-semibold uppercase tracking-wide text-slate-600">
          Airport Breakdown
        </h3>
        <div class="grid gap-3">
          <div
            v-for="metric in destination.airport_breakdown"
            :key="`${destination.destination_iata}-${metric.key}`"
            class="rounded-xl border border-white/70 bg-white/62 p-3 shadow-sm backdrop-blur-sm"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="flex gap-3">
                <div
                  v-if="metric.key && iconMap[metric.key]"
                  class="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-600"
                >
                  <component :is="iconMap[metric.key]" class="h-4 w-4" />
                </div>
                <div>
                  <p class="font-medium text-slate-900">{{ metric.label || metric.key }}</p>
                  <p class="mt-1 text-sm text-slate-500">Target: {{ metric.target || 'N/A' }}</p>
                  <p class="text-sm text-slate-500">Actual: {{ metric.actual || 'N/A' }}</p>
                </div>
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
        <h3 class="text-sm font-semibold uppercase tracking-wide text-slate-600">
          Best Flight Per Origin
        </h3>
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
              <span
                class="rounded-full px-2.5 py-1"
                :class="scoreBadgeClass(flight.scores?.flight_time)"
              >
                Time {{ formatPercent(flight.scores?.flight_time) }}
              </span>
              <span
                class="rounded-full px-2.5 py-1"
                :class="scoreBadgeClass(flight.scores?.flight_cost)"
              >
                Cost {{ formatPercent(flight.scores?.flight_cost) }}
              </span>
              <span
                class="rounded-full px-2.5 py-1"
                :class="scoreBadgeClass(flight.scores?.departure_date)"
              >
                Date {{ formatPercent(flight.scores?.departure_date) }}
              </span>
            </div>
            <div class="mt-3 grid gap-3 text-sm text-slate-600 sm:grid-cols-2 lg:grid-cols-3">
              <div class="flex items-center gap-2">
                <Calendar class="h-4 w-4 text-slate-400" />
                <span>Depart: {{ formatDateTime(flight.departure_scheduled) }}</span>
              </div>
              <div class="flex items-center gap-2">
                <Calendar class="h-4 w-4 text-slate-400" />
                <span>Arrive: {{ formatDateTime(flight.arrival_scheduled) }}</span>
              </div>
              <div class="flex items-center gap-2">
                <Clock class="h-4 w-4 text-slate-400" />
                <span>Duration: {{ formatDuration(flight.duration_hours) }}</span>
              </div>
              <div class="flex items-center gap-2">
                <CircleDollarSign class="h-4 w-4 text-slate-400" />
                <span>Est. Cost: {{ formatMoney(flight.estimated_cost_usd) }}</span>
              </div>
              <div class="flex items-center gap-2">
                <Layers class="h-4 w-4 text-slate-400" />
                <span>Options: {{ flight.option_count ?? 'N/A' }}</span>
              </div>
              <div class="flex items-center gap-2">
                <Trophy class="h-4 w-4 text-slate-400" />
                <span>Flight Rank: {{ flight.flight_rank ?? 'N/A' }}</span>
              </div>
            </div>
          </div>
        </div>
      </section>
    </CardContent>
  </Card>
</template>

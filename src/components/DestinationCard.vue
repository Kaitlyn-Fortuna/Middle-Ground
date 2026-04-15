<script setup lang="ts">
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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
          class="rounded-full px-3 py-1 text-slate-800 ring-1 ring-black/5 backdrop-blur-sm"
          :class="scoreBadgeClass(destination.airport_score)"
        >
          Airport #{{ destination.airport_rank ?? 'N/A' }} ·
          {{ formatPercent(destination.airport_score) }}
        </span>
        <span
          class="rounded-full px-3 py-1 text-slate-800 ring-1 ring-black/5 backdrop-blur-sm"
          :class="scoreBadgeClass(destination.flight_score)"
        >
          Flights #{{ destination.flight_rank ?? 'N/A' }} ·
          {{ formatPercent(destination.flight_score) }}
        </span>
        <span
          class="rounded-full bg-slate-900/6 px-3 py-1 text-slate-800 ring-1 ring-black/5 backdrop-blur-sm"
        >
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
</template>

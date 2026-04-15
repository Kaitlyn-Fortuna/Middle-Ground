<script setup lang="ts">
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import DestinationCard from './DestinationCard.vue'
import type { DestinationResultRow, RankDiagnostics } from '@/types'

defineProps<{
  resultRows: DestinationResultRow[]
  resultDiagnostics: RankDiagnostics | null
  responseOrigins: string[]
  departureDate: string
  returnDate: string
  summaryMessage: string | null
  searchError: string | null
  activeScoreKeys: { airport: string[]; flight: string[] }
}>()

defineEmits<{
  editSearch: []
}>()
</script>

<template>
  <div class="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-5 py-6 lg:px-6">
    <div class="mb-6 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
      <div>
        <p class="text-xs font-semibold uppercase tracking-[0.28em] text-sky-700">Results</p>
        <h1 class="mt-2 text-3xl font-semibold tracking-tight text-slate-900 lg:text-[2rem]">
          {{
            resultRows.length
              ? `Found ${resultRows.length} shared destinations`
              : 'No shared destinations found'
          }}
        </h1>
        <p class="mt-2 max-w-3xl text-sm text-slate-600 lg:text-base">
          Origins:
          <strong>{{ responseOrigins.join(', ') || 'N/A' }}</strong>
          <span class="mx-2 text-slate-300">|</span>
          Dates:
          <strong>{{ departureDate }}</strong>
          to
          <strong>{{ returnDate }}</strong>
        </p>
      </div>
      <Button variant="outline" class="cursor-pointer self-start" @click="$emit('editSearch')">
        Edit Search
      </Button>
    </div>

    <Alert v-if="summaryMessage" :variant="searchError ? 'destructive' : 'default'" class="mb-6">
      <AlertTitle>{{ searchError ? 'Search failed' : 'Search note' }}</AlertTitle>
      <AlertDescription>{{ summaryMessage }}</AlertDescription>
    </Alert>

    <div v-if="resultRows.length" class="space-y-5">
      <DestinationCard
        v-for="destination in resultRows"
        :key="`${destination.destination_iata}-${destination.rank}`"
        :destination="destination"
      />
    </div>

    <div v-if="resultRows.length" class="mt-6 space-y-4">
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
            {{ routeError.origin_iata }} → {{ routeError.destination_iata }}:
            {{ routeError.error }}
          </p>
        </CardContent>
      </Card>
      <Card class="border-white/70 bg-white/74 shadow-lg backdrop-blur-md">
        <CardHeader>
          <CardTitle class="text-base">Backend Summary</CardTitle>
        </CardHeader>
        <CardContent class="flex flex-wrap gap-3 text-sm text-slate-700">
          <span class="rounded-full bg-slate-100/85 px-3 py-1"
            >Live flights loaded: {{ resultDiagnostics?.live_flights_loaded ?? 'N/A' }}</span
          >
          <span class="rounded-full bg-slate-100/85 px-3 py-1">
            Candidate destinations considered:
            {{ resultDiagnostics?.candidate_destinations_considered?.length ?? 0 }}
          </span>
          <span class="rounded-full bg-slate-100/85 px-3 py-1">
            Airport score keys: {{ activeScoreKeys.airport.join(', ') || 'None' }}
          </span>
          <span class="rounded-full bg-slate-100/85 px-3 py-1">
            Flight score keys: {{ activeScoreKeys.flight.join(', ') || 'None' }}
          </span>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

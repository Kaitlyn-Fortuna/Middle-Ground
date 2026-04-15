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
import { getLocalTimeZone } from '@internationalized/date'
import type { DateRange } from 'reka-ui'
import { computed, nextTick, ref } from 'vue'
import type { AirportOption, GroupMemberHandle } from '@/types'
import { formatMoney } from '@/lib/formatters'

const props = defineProps<{
  airportOptions: AirportOption[]
  loadingAirports: boolean
  airportLoadError: string | null
  isSearchReady: boolean
}>()

const emit = defineEmits<{
  search: []
  loadAirports: []
}>()

const groupMembers = defineModel<string[][]>('groupMembers', { required: true })
const dateRange = defineModel<DateRange>('dateRange', { required: true })
const budget = defineModel<number[]>('budget', { required: true })
const maxFlightTime = defineModel<number[]>('maxFlightTime', { required: true })
const preferences = defineModel<Record<string, boolean>>('preferences', { required: true })

const groupMemberRefs = ref<Array<GroupMemberHandle | null>>([])

const firstEmptyGroupMemberIndex = computed(() =>
  groupMembers.value.findIndex((member) => !member[0]?.trim()),
)

function setGroupMemberRef(index: number, instance: GroupMemberHandle | null) {
  groupMemberRefs.value[index] = instance
}

function focusGroupMember(index: number) {
  void nextTick(() => {
    groupMemberRefs.value[index]?.focusInput()
  })
}

function addOrFocusGroupMember() {
  if (firstEmptyGroupMemberIndex.value !== -1) {
    focusGroupMember(firstEmptyGroupMemberIndex.value)
    return
  }

  groupMembers.value.push([])
  focusGroupMember(groupMembers.value.length - 1)
}

function handleGroupMemberAdvance(index: number) {
  const otherEmptyIndex = groupMembers.value.findIndex(
    (member, memberIndex) => memberIndex !== index && !member[0]?.trim(),
  )
  if (otherEmptyIndex !== -1) {
    focusGroupMember(otherEmptyIndex)
    return
  }

  groupMembers.value.push([])
  focusGroupMember(groupMembers.value.length - 1)
}
</script>

<template>
  <div class="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-5 py-5 lg:px-6 lg:py-6">
    <div class="mb-5">
      <p class="text-xs font-semibold uppercase tracking-[0.28em] text-sky-700">Middle Ground</p>
      <h1 class="mt-2 text-3xl font-semibold tracking-tight text-slate-900 lg:text-[2rem]">
        Plan a destination everyone can actually reach.
      </h1>
      <p class="mt-2 max-w-3xl text-sm text-slate-600 lg:text-base">
        Pick one home airport per traveler, choose the kind of trip your group wants, and we'll
        compare the best shared destinations for everyone.
      </p>
    </div>

    <Alert v-if="airportLoadError" variant="destructive" class="mb-6">
      <AlertTitle>Airport list unavailable</AlertTitle>
      <AlertDescription class="flex items-center justify-between gap-4">
        <span>{{ airportLoadError }}</span>
        <Button variant="outline" size="sm" class="cursor-pointer" @click="$emit('loadAirports')">
          Retry
        </Button>
      </AlertDescription>
    </Alert>

    <div class="grid flex-1 min-h-0 gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
      <Card class="flex min-h-0 border-white/70 bg-white/72 shadow-lg backdrop-blur-md">
        <CardHeader>
          <CardTitle>Group Members</CardTitle>
          <CardDescription>Pick the airport each person would realistically depart from.</CardDescription>
        </CardHeader>
        <CardContent class="flex min-h-0 flex-1 flex-col gap-3">
          <div class="min-h-[20rem] flex-1 space-y-3 overflow-auto rounded-xl bg-slate-50/80 p-3">
            <div
              v-if="groupMembers.length === 0"
              class="rounded-lg border border-dashed border-slate-300 p-4 text-sm text-slate-500"
            >
              No group members added yet.
            </div>
            <GroupMember
              v-for="(member, index) in groupMembers"
              :key="index"
              :ref="(instance) => setGroupMemberRef(index, instance as GroupMemberHandle | null)"
              v-model:airports="groupMembers[index]"
              :airport-options="airportOptions"
              :loading-airports="loadingAirports"
              :delete-member="() => groupMembers.splice(index, 1)"
              @advance="handleGroupMemberAdvance(index)"
            />
          </div>
          <div class="mt-auto space-y-4 border-t border-slate-200/70 pt-3">
            <p class="text-xs text-slate-500">
              Tip: two or more travelers makes the results much more useful.
            </p>
            <div class="flex flex-col gap-2">
              <Button
                class="cursor-pointer self-start"
                size="sm"
                variant="outline"
                @click="addOrFocusGroupMember"
              >
                <Plus class="mr-1 h-4 w-4" />
                Add Group Member
              </Button>
            </div>
            <div class="space-y-2 border-t border-slate-200/70 pt-3">
              <Button :disabled="!isSearchReady" class="cursor-pointer w-full" @click="$emit('search')">
                <Plane class="mr-2 h-4 w-4" />
                Search Shared Destinations
              </Button>
              <p class="text-sm text-slate-500">
                {{
                  isSearchReady
                    ? 'Ready to compare the best shared destinations.'
                    : 'Add at least two travelers and select one airport for each to start.'
                }}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card class="border-white/70 bg-white/72 shadow-lg backdrop-blur-md">
        <CardHeader>
          <CardTitle>Preferences</CardTitle>
          <CardDescription>Set the trip window and the kind of destination your group would enjoy most.</CardDescription>
        </CardHeader>
        <CardContent class="space-y-2.5">
          <section class="rounded-2xl bg-slate-50/80 px-3.5 py-2.5">
            <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div class="max-w-sm">
                <h2 class="text-sm font-semibold uppercase tracking-wide text-slate-700">Dates</h2>
                <p class="mt-1 text-sm text-slate-500">
                  Choose the travel window your group can realistically make work.
                </p>
              </div>
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

          <section class="rounded-2xl bg-slate-50/80 px-3.5 py-2.5">
            <div class="space-y-2.5">
              <div>
                <h2 class="text-sm font-semibold uppercase tracking-wide text-slate-700">Temperature</h2>
                <p class="mt-1 text-sm text-slate-500">Set the kind of climate the group would enjoy.</p>
              </div>
              <div class="grid grid-cols-2 gap-2 sm:grid-cols-5">
                <PreferenceButton :icon="Sun" v-model="preferences.hot">Hot</PreferenceButton>
                <PreferenceButton :icon="SunDim" v-model="preferences.warm">Warm</PreferenceButton>
                <PreferenceButton :icon="Thermometer" v-model="preferences.mild">Mild</PreferenceButton>
                <PreferenceButton :icon="Wind" v-model="preferences.cool">Cool</PreferenceButton>
                <PreferenceButton :icon="Snowflake" v-model="preferences.cold">Cold</PreferenceButton>
              </div>
            </div>
          </section>

          <section class="rounded-2xl bg-slate-50/80 px-3.5 py-2.5">
            <div class="space-y-2.5">
              <div>
                <h2 class="text-sm font-semibold uppercase tracking-wide text-slate-700">Conditions</h2>
                <p class="mt-1 text-sm text-slate-500">
                  Choose the overall feel of the weather, from sunny to humid.
                </p>
              </div>
              <div class="grid grid-cols-2 gap-2 sm:grid-cols-5">
                <PreferenceButton :icon="Sun" v-model="preferences.sunny">Sunny</PreferenceButton>
                <PreferenceButton :icon="SunDim" v-model="preferences.arid">Arid</PreferenceButton>
                <PreferenceButton :icon="CloudRain" v-model="preferences.rainy">Rainy</PreferenceButton>
                <PreferenceButton :icon="DropletOff" v-model="preferences.dry">Dry</PreferenceButton>
                <PreferenceButton :icon="Droplets" v-model="preferences.humid">Humid</PreferenceButton>
              </div>
            </div>
          </section>

          <section class="rounded-2xl bg-slate-50/80 px-3.5 py-2.5">
            <div class="space-y-2.5">
              <div>
                <h2 class="text-sm font-semibold uppercase tracking-wide text-slate-700">Geography</h2>
                <p class="mt-1 text-sm text-slate-500">
                  Tell the app what kind of place would feel right for the group.
                </p>
              </div>
              <div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
                <PreferenceButton :icon="TreePalm" v-model="preferences.beach">Beach</PreferenceButton>
                <PreferenceButton :icon="Waves" v-model="preferences.coastal">Coastal</PreferenceButton>
                <PreferenceButton :icon="Building2" v-model="preferences.urban">Urban</PreferenceButton>
                <PreferenceButton :icon="Mountain" v-model="preferences.mountain">
                  Mountains
                </PreferenceButton>
              </div>
            </div>
          </section>

          <section class="rounded-2xl bg-slate-50/80 px-3.5 py-2.5">
            <div class="space-y-2.5">
              <div>
                <h2 class="text-sm font-semibold uppercase tracking-wide text-slate-700">Trip Limits</h2>
                <p class="mt-1 text-sm text-slate-500">
                  Keep the results within a range that still feels realistic for the group.
                </p>
              </div>
              <div class="grid gap-3 xl:grid-cols-2">
                <div class="flex flex-col gap-2.5 rounded-xl bg-white/70 px-3.5 py-2.5 shadow-sm">
                  <div class="space-y-1.5">
                    <div>
                      <h3 class="text-sm font-semibold uppercase tracking-wide text-slate-700">
                        Max Flight Cost
                      </h3>
                      <p class="mt-1 text-sm text-slate-500">
                        Keep pricier flight options from floating to the top.
                      </p>
                    </div>
                    <span
                      class="inline-flex w-fit rounded-full bg-sky-100/90 px-3 py-1 text-sm font-semibold text-sky-950"
                    >
                      {{ formatMoney(budget[0]) }}
                    </span>
                  </div>
                  <Slider v-model="budget" :max="1000" :min="100" :step="25" />
                </div>
                <div class="flex flex-col gap-2.5 rounded-xl bg-white/70 px-3.5 py-2.5 shadow-sm">
                  <div class="space-y-1.5">
                    <div>
                      <h3 class="text-sm font-semibold uppercase tracking-wide text-slate-700">
                        Max Flight Time
                      </h3>
                      <p class="mt-1 text-sm text-slate-500">
                        Shorter limits favor destinations that are easier on the whole group.
                      </p>
                    </div>
                    <span
                      class="inline-flex w-fit rounded-full bg-sky-100/90 px-3 py-1 text-sm font-semibold text-sky-950"
                    >
                      {{ maxFlightTime[0] }} hr
                    </span>
                  </div>
                  <Slider v-model="maxFlightTime" :max="16" :min="2" :step="1" />
                </div>
              </div>
            </div>
          </section>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { RangeCalendar } from '@/components/ui/range-calendar'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Slider } from '@/components/ui/slider'
import { computed, ref, type Ref } from 'vue'
import {
  Plane,
  Plus,
  Sun,
  SunDim,
  Thermometer,
  Wind,
  Snowflake,
  DropletOff,
  CloudRain,
  TreePalm,
  Mountain,
  Building2,
  Waves,
  Icon,
  Droplets,
  Star,
} from '@lucide/vue'
import { cactus, palmtreeIslandSun } from '@lucide/lab'
import GroupMember from '@/components/GroupMember.vue'
import PreferenceButton from '@/components/PreferenceButton.vue'
import { h } from 'vue'
import type { DateRange } from 'reka-ui'
import { getLocalTimeZone, today } from '@internationalized/date'
import { useFetch } from '@vueuse/core'

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

const budget = ref([200])
const maxFlightTime = ref([12])

const phase = ref<'setup' | 'searching' | 'done'>('setup')

const requestBody = computed(() => {
  const airports = groupMembers.value.map((member) => member[0])
  return {
    departure_date: dateRange?.value?.start?.toString() || '',
    return_date: dateRange?.value?.end?.toString() || '',
    airports: airports,
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
    budget_cap: budget.value[0],
    max_flight_cost: budget.value[0],
    max_flight_time: maxFlightTime.value[0],
    max_connections: 1,
    prefer_nonstop: true,
    domestic_only: true,
  }
})

const { data, isFetching, error, execute, onFetchResponse } = useFetch(
  'http://localhost:5001/api/search',
  { immediate: false },
)
  .post(requestBody.value)
  .json()

async function search() {
  console.log(requestBody.value)
  phase.value = 'searching'
  await execute()
  phase.value = 'done'
}
</script>

<template>
  <div class="w-screen overflow-x-hidden">
    <Transition mode="out-in">
      <div
        class="flex flex-col w-screen items-center justify-center py-10"
        v-if="phase === 'setup'"
      >
        <h1 class="text-3xl font-bold mb-4">Middle Ground</h1>
        <div class="w-full flex justify-center gap-4">
          <Card class="w-full max-w-md">
            <CardHeader>
              <CardTitle>Welcome!</CardTitle>
              <CardDescription>To start, enter the home airport codes.</CardDescription>
            </CardHeader>
            <CardContent>
              <h2 class="font-bold mb-2">Group Members</h2>
              <div class="flex flex-col gap-2 bg-secondary rounded-md p-2">
                <div v-if="groupMembers.length === 0">
                  <p class="text-muted-foreground text-sm">No group members added</p>
                </div>
                <GroupMember
                  v-for="(member, index) in groupMembers"
                  :key="index"
                  v-model:airports="groupMembers[index]"
                  :delete-member="() => groupMembers.splice(index, 1)"
                />
              </div>
              <Button
                class="cursor-pointer mt-2"
                size="sm"
                variant="outline"
                @click="groupMembers.push([])"
                ><Plus />Add Group Member</Button
              >
            </CardContent>
          </Card>
          <Card class="gap-2">
            <CardHeader>
              <CardTitle class="text-lg pb-0">Preferences</CardTitle>
            </CardHeader>
            <CardContent class="flex flex-col gap-2">
              <h1 class="font-bold">Dates</h1>
              <div class="px-4 py-2 bg-secondary rounded-md">
                <Popover>
                  <PopoverTrigger>
                    <Button variant="outline">
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
              <h1 class="font-bold">Weather</h1>
              <div class="px-4 pt-2 pb-4 bg-secondary rounded-md">
                <h2 class="font-semibold mb-1 text-sm">Temperature</h2>
                <div class="grid grid-cols-5 gap-2">
                  <PreferenceButton :icon="Sun" v-model="hotPreference">Hot</PreferenceButton>
                  <PreferenceButton :icon="SunDim" v-model="warmPreference">Warm</PreferenceButton>
                  <PreferenceButton :icon="Thermometer" v-model="mildPreference"
                    >Mild</PreferenceButton
                  >
                  <PreferenceButton :icon="Wind" v-model="coolPreference">Cool</PreferenceButton>
                  <PreferenceButton :icon="Snowflake" v-model="coldPreference"
                    >Cold</PreferenceButton
                  >
                </div>
              </div>
              <div class="px-4 pt-2 pb-4 bg-secondary rounded-md">
                <h2 class="font-semibold mb-1 text-sm">Conditions</h2>
                <div class="grid grid-cols-5 gap-2">
                  <PreferenceButton :icon="Sun" v-model="sunnyPreference">Sunny</PreferenceButton>
                  <PreferenceButton
                    :icon="() => h(Icon, { iconNode: cactus })"
                    v-model="aridPreference"
                    >Arid</PreferenceButton
                  >
                  <PreferenceButton :icon="CloudRain" v-model="rainyPreference"
                    >Rainy</PreferenceButton
                  >
                  <PreferenceButton :icon="DropletOff" v-model="dryPreference"
                    >Dry</PreferenceButton
                  >
                  <PreferenceButton :icon="Droplets" v-model="humidPreference"
                    >Humid</PreferenceButton
                  >
                </div>
              </div>
              <h1 class="font-bold">Geography</h1>
              <div class="px-4 pt-2 pb-4 bg-secondary rounded-md">
                <h2 class="font-semibold mb-1 text-sm">Environment</h2>
                <div class="grid grid-cols-4 gap-2">
                  <PreferenceButton :icon="TreePalm" v-model="beachPreference"
                    >Beach</PreferenceButton
                  >
                  <PreferenceButton :icon="Waves" v-model="coastalPreference"
                    >Coastal</PreferenceButton
                  >
                  <PreferenceButton :icon="Building2" v-model="urbanPreference"
                    >Urban</PreferenceButton
                  >
                  <PreferenceButton :icon="Mountain" v-model="mountainPreference"
                    >Mountains</PreferenceButton
                  >
                </div>
              </div>
              <h1 class="font-bold">Budget</h1>
              <div class="py-2 bg-background rounded-md">
                <Slider v-model="budget" :max="1000" :min="0" :step="50" />
                <p>${{ budget[0] }}</p>
              </div>
              <h1 class="font-bold">Max Flight Time</h1>
              <div class="py-2 bg-background rounded-md">
                <Slider v-model="maxFlightTime" :max="30" :min="2" :step="1" />
                <p>{{ maxFlightTime[0] }} hours</p>
              </div>
            </CardContent>
          </Card>
        </div>
        <Button :disabled="groupMembers.length < 2" class="cursor-pointer mt-4" @click="search">
          <Plane />Begin Search
        </Button>
      </div>
      <div
        class="flex flex-col h-screen w-screen items-center justify-center"
        v-else-if="phase === 'searching'"
      >
        <h1 class="text-3xl font-bold mb-4 text-muted-foreground">Searching...</h1>
      </div>
    </Transition>
  </div>
</template>

<style>
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

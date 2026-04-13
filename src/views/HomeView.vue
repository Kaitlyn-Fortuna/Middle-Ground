<script setup lang="ts">
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { RangeCalendar } from '@/components/ui/range-calendar'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { ref, type Ref } from 'vue'
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

const groupMembers = ref<string[][]>([])

const start = today(getLocalTimeZone())
const end = start.add({ days: 7 })
const dateRange = ref({
  start,
  end,
}) as Ref<DateRange>
</script>

<template>
  <div class="flex flex-col h-screen w-screen items-center justify-center">
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
      <Card>
        <CardHeader>
          <CardTitle class="text-lg">Preferences</CardTitle>
        </CardHeader>
        <CardContent class="flex flex-col gap-2">
          <h1 class="font-bold">Dates</h1>
          <div class="px-4 py-2 bg-secondary rounded-md w-1/3">
            <Popover>
              <PopoverTrigger>
                <Button variant="outline">
                  {{ dateRange?.start?.toDate(getLocalTimeZone()).toLocaleDateString() ?? '?' }} -
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
              <PreferenceButton :icon="Sun">Hot</PreferenceButton>
              <PreferenceButton :icon="SunDim">Warm</PreferenceButton>
              <PreferenceButton :icon="Thermometer">Mild</PreferenceButton>
              <PreferenceButton :icon="Wind">Cool</PreferenceButton>
              <PreferenceButton :icon="Snowflake">Cold</PreferenceButton>
            </div>
          </div>
          <div class="px-4 pt-2 pb-4 bg-secondary rounded-md">
            <h2 class="font-semibold mb-1 text-sm">Conditions</h2>
            <div class="grid grid-cols-5 gap-2">
              <PreferenceButton :icon="Sun">Sunny</PreferenceButton>
              <PreferenceButton :icon="() => h(Icon, { iconNode: cactus })">Arid</PreferenceButton>
              <PreferenceButton :icon="CloudRain">Rainy</PreferenceButton>
              <PreferenceButton :icon="DropletOff">Dry</PreferenceButton>
              <PreferenceButton :icon="Droplets">Humid</PreferenceButton>
            </div>
          </div>
          <h1 class="font-bold">Geography</h1>
          <div class="px-4 pt-2 pb-4 bg-secondary rounded-md">
            <h2 class="font-semibold mb-1 text-sm">Environment</h2>
            <div class="grid grid-cols-5 gap-2">
              <PreferenceButton :icon="TreePalm">Beach</PreferenceButton>
              <PreferenceButton :icon="Waves">Coastal</PreferenceButton>
              <PreferenceButton :icon="() => h(Icon, { iconNode: palmtreeIslandSun })"
                >Island</PreferenceButton
              >
              <PreferenceButton :icon="Building2">Urban</PreferenceButton>
              <PreferenceButton :icon="Mountain">Mountains</PreferenceButton>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
    <Button :disabled="groupMembers.length < 2" class="cursor-pointer mt-4"
      ><Plane />Begin Search</Button
    >
  </div>
</template>

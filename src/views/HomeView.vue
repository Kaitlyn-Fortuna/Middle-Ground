<script setup lang="ts">
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ref } from 'vue'
import {
  Plane,
  Plus,
  Sun,
  SunDim,
  Thermometer,
  Wind,
  Snowflake,
  Droplet,
  DropletOff,
  CloudSun,
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

const groupMembers = ref<string[][]>([])
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
          <h1 class="font-bold">Weather</h1>
          <div class="px-4 pt-2 pb-4 bg-secondary rounded-md">
            <h2 class="font-semibold mb-1 text-sm">Temperature</h2>
            <div class="grid grid-cols-5 gap-2">
              <Button variant="outline"><Sun />Hot</Button>
              <Button variant="outline"><SunDim />Warm</Button>
              <Button variant="outline"><Thermometer />Mild</Button>
              <Button variant="outline"><Wind />Cool</Button>
              <Button variant="outline"><Snowflake />Cold</Button>
            </div>
          </div>
          <div class="px-4 pt-2 pb-4 bg-secondary rounded-md">
            <h2 class="font-semibold mb-1 text-sm">Conditions</h2>
            <div class="grid grid-cols-5 gap-2">
              <Button
                variant="outline"
                class="border-sky-500 border-3 bg-sky-100 relative hover:bg-sky-200 cursor-pointer group"
              >
                <Sun />Sunny
                <div
                  class="absolute -right-1 -top-1 bg-sky-200/90 text-sky-600 rounded-full p-1 group-hover:bg-sky-300/90 group-hover:text-sky-600 transition-all duration-200"
                >
                  <Star />
                </div>
              </Button>
              <Button variant="outline"><Icon :iconNode="cactus" />Arid</Button>
              <Button variant="outline"><CloudRain />Rainy</Button>
              <Button variant="outline" class="border-amber-500 border-3 bg-amber-100 relative">
                <DropletOff />Dry
                <div
                  class="absolute -right-1 -top-1 bg-amber-200/90 text-amber-600 rounded-full p-1"
                >
                  <Star fill="currentColor" />
                </div>
              </Button>
              <Button variant="outline"><Droplets />Humid</Button>
            </div>
          </div>
          <h1 class="font-bold">Geography</h1>
          <div class="px-4 pt-2 pb-4 bg-secondary rounded-md">
            <h2 class="font-semibold mb-1 text-sm">Environment</h2>
            <div class="grid grid-cols-5 gap-2">
              <Button variant="outline"><TreePalm />Beach</Button>
              <Button variant="outline"><Waves />Coastal</Button>
              <Button variant="outline"><Icon :iconNode="palmtreeIslandSun" />Island</Button>
              <Button variant="outline"><Building2 />Urban</Button>
              <Button variant="outline"><Mountain />Mountains</Button>
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

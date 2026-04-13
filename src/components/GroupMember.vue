<script setup lang="ts">
import { Field } from '@/components/ui/field'
import { TagsInput, TagsInputItem, TagsInputItemDelete } from '@/components/ui/tags-input'
import { Button } from '@/components/ui/button'
import { Trash } from 'lucide-vue-next'
import {
  ComboboxRoot,
  ComboboxAnchor,
  ComboboxInput,
  ComboboxPortal,
  ComboboxContent,
  ComboboxGroup,
  ComboboxItem,
} from 'reka-ui'
import airportOptionsRaw from '../../airport_options.json'
import { ref, computed } from 'vue'

interface Airport {
  iata_code: string
  name: string
  municipality: string
  iso_country: string
  type: string
}

const airportOptions = airportOptionsRaw as Airport[]

defineProps<{
  deleteMember: () => void
}>()

// Filter out already selected items and apply search term manually
// Limit to 50 results so the massive airport json doesn't lag the DOM
const open = ref(false)
const searchTerm = ref('')
const modelValue = defineModel<string[]>('airports')

const filteredAirports = computed(() => {
  const search = searchTerm.value.toLowerCase().trim()
  if (!search) {
    return airportOptions
      .filter((airport) => modelValue.value!.includes(airport.iata_code))
      .slice(0, 50)
  }

  const results: { airport: Airport; score: number }[] = []

  for (const airport of airportOptions) {
    if (modelValue.value!.includes(airport.iata_code)) continue

    const code = airport.iata_code.toLowerCase()
    const name = airport.name.toLowerCase()
    const city = airport.municipality.toLowerCase()
    const country = airport.iso_country ? airport.iso_country.toLowerCase() : ''

    let score = 0

    if (code === search) score = 100
    else if (code.startsWith(search)) score = 50
    else if (city === search) score = 45
    else if (city.startsWith(search)) score = 40
    else if (name.startsWith(search)) score = 30
    else if (code.includes(search)) score = 15
    else if (city.includes(search)) score = 10
    else if (name.includes(search)) score = 5
    else if (country === search) score = 1

    if (score > 0) {
      results.push({ airport, score })
    }
  }

  results.sort((a, b) => b.score - a.score)

  return results.slice(0, 50).map((r) => r.airport)
})

function handleSelect(airport: Airport) {
  modelValue.value!.push(airport.iata_code)
  open.value = false

  // Delay clearing the search term slightly so the dropdown doesn't
  // show all items during its closing animation.
  setTimeout(() => {
    searchTerm.value = ''
  }, 0)
}
</script>

<template>
  <div class="flex w-full gap-1 items-center">
    <div class="flex w-full max-w-sm flex-col gap-4">
      <ComboboxRoot
        v-model="modelValue"
        v-model:open="open"
        v-model:searchTerm="searchTerm"
        class="relative w-full"
        multiple
        :reset-search-term-on-blur="false"
      >
        <ComboboxAnchor as-child>
          <div class="relative w-full">
            <TagsInput
              :model-value="modelValue"
              @update:model-value="modelValue = $event"
              class="flex w-full flex-wrap gap-2 px-2 py-1"
            >
              <TagsInputItem v-for="item in modelValue" :key="item" :value="item">
                <span class="py-0.5 px-2 text-sm rounded bg-transparent">
                  {{
                    (() => {
                      const a = airportOptions.find((a) => a.iata_code === item)
                      return a ? `${a.iata_code}` : item
                    })()
                  }}
                </span>
                <TagsInputItemDelete />
              </TagsInputItem>

              <ComboboxInput
                :value="searchTerm"
                @input="(e: Event) => (searchTerm = (e.target as HTMLInputElement).value)"
                placeholder="Search airports..."
                class="flex-1 bg-transparent border-none outline-none ring-0 shadow-none min-w-[120px] text-sm min-h-5 px-1"
                @keydown.enter.prevent
                @keydown.backspace="
                  (e: KeyboardEvent) => {
                    if (searchTerm === '' && modelValue.length > 0) {
                      modelValue.pop()
                    }
                  }
                "
              />
            </TagsInput>
          </div>
        </ComboboxAnchor>

        <ComboboxPortal>
          <ComboboxContent
            position="popper"
            align="start"
            class="z-50 w-[--reka-popper-anchor-width] p-0 mt-2 overflow-hidden rounded-md border bg-popover text-popover-foreground shadow-md data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2"
          >
            <div
              v-if="filteredAirports.length === 0"
              class="py-6 text-center text-sm text-muted-foreground"
            >
              No airports found.
            </div>

            <ComboboxGroup v-else class="overflow-y-auto max-h-60 p-1 text-foreground">
              <ComboboxItem
                v-for="airport in filteredAirports"
                :key="airport.iata_code"
                :value="airport.iata_code"
                class="relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50"
                @select.prevent="handleSelect(airport)"
              >
                <div class="flex flex-col w-full text-left">
                  <span class="font-medium">[{{ airport.iata_code }}] {{ airport.name }}</span>
                  <span class="text-xs text-muted-foreground"
                    >{{ airport.municipality }}, {{ airport.iso_country }}</span
                  >
                </div>
              </ComboboxItem>
            </ComboboxGroup>
          </ComboboxContent>
        </ComboboxPortal>
      </ComboboxRoot>
    </div>
    <Button
      variant="ghost"
      size="icon"
      @click="deleteMember"
      class="cursor-pointer text-red-500 hover:bg-red-500/80"
      ><Trash
    /></Button>
  </div>
</template>

<script setup lang="ts">
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
  type AcceptableInputValue,
} from 'reka-ui'
import { computed, nextTick, ref } from 'vue'

interface Airport {
  iata_code: string
  name: string
  municipality: string
  iso_region: string
}

const props = withDefaults(
  defineProps<{
    airportOptions: Airport[]
    loadingAirports?: boolean
    deleteMember: () => void
  }>(),
  {
    loadingAirports: false,
  },
)
const emit = defineEmits<{
  advance: []
}>()

const selectedAirports = computed(() => modelValue.value ?? [])

// Filter out already selected items and apply search term manually
// Limit to 50 results so the airport list doesn't lag the DOM.
const open = ref(false)
const searchTerm = ref('')
const modelValue = defineModel<string[]>('airports', { default: [] })
const rootEl = ref<HTMLElement | null>(null)

const filteredAirports = computed(() => {
  const search = searchTerm.value.toLowerCase().trim()
  const availableAirports = props.airportOptions

  if (!search) {
    return availableAirports
      .filter((airport) => !selectedAirports.value.includes(airport.iata_code))
      .slice(0, 50)
  }

  const results: { airport: Airport; score: number }[] = []

  for (const airport of availableAirports) {
    if (selectedAirports.value.includes(airport.iata_code)) continue

    const code = airport.iata_code.toLowerCase()
    const name = airport.name.toLowerCase()
    const city = airport.municipality.toLowerCase()
    const region = airport.iso_region ? airport.iso_region.toLowerCase() : ''

    let score = 0

    if (code === search) score = 100
    else if (code.startsWith(search)) score = 50
    else if (city === search) score = 45
    else if (city.startsWith(search)) score = 40
    else if (name.startsWith(search)) score = 30
    else if (code.includes(search)) score = 15
    else if (city.includes(search)) score = 10
    else if (name.includes(search)) score = 5
    else if (region === search) score = 1

    if (score > 0) {
      results.push({ airport, score })
    }
  }

  results.sort((a, b) => b.score - a.score)

  return results.slice(0, 50).map((result) => result.airport)
})

function handleSelect(airport: Airport, options?: { advance?: boolean }) {
  modelValue.value = [airport.iata_code]
  open.value = false

  // Delay clearing the search term slightly so the dropdown doesn't
  // show all items during its closing animation.
  setTimeout(() => {
    searchTerm.value = ''
  }, 0)

  if (options?.advance) {
    emit('advance')
  }
}

function updateModelValue(values: AcceptableInputValue[]) {
  modelValue.value = values.map((value) => String(value)).slice(-1)
}

const isLocked = computed(() => selectedAirports.value.length >= 1)

function completeWithTopMatchAndAdvance(event: KeyboardEvent) {
  const bestMatch = filteredAirports.value[0]
  if (!bestMatch || !searchTerm.value.trim()) return

  event.preventDefault()
  handleSelect(bestMatch, { advance: true })
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Backspace' && searchTerm.value === '' && modelValue.value.length > 0) {
    modelValue.value.pop()
    return
  }

  if (event.key === 'Escape') {
    event.preventDefault()

    if (!searchTerm.value.trim() && modelValue.value.length === 0) {
      props.deleteMember()
      return
    }

    open.value = false
    searchTerm.value = ''
    ;(event.target as HTMLInputElement | null)?.blur()
    return
  }

  if (event.key === 'Enter' || event.key === 'Tab' || event.key === ' ') {
    completeWithTopMatchAndAdvance(event)
  }
}

function focusInput() {
  if (isLocked.value) return

  open.value = true
  void nextTick(() => {
    const input = rootEl.value?.querySelector('input')
    if (!(input instanceof HTMLInputElement)) return
    input.focus()
    input.select()
  })
}

defineExpose({
  focusInput,
})
</script>

<template>
  <div ref="rootEl" class="flex w-full gap-1 items-center">
    <div class="flex w-full flex-col">
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
              @update:model-value="updateModelValue"
              class="flex min-h-12 w-full flex-wrap gap-2 rounded-xl border border-white/70 bg-white/78 px-2 py-1.5 shadow-sm backdrop-blur-sm"
            >
              <TagsInputItem v-for="item in modelValue" :key="item" :value="item">
                <span class="rounded bg-transparent px-2 py-0.5 text-sm font-medium">
                  {{
                    (() => {
                      const a = props.airportOptions.find((airport) => airport.iata_code === item)
                      return a ? `${a.iata_code} - ${a.municipality}` : item
                    })()
                  }}
                </span>
                <TagsInputItemDelete />
              </TagsInputItem>

              <ComboboxInput
                v-if="!isLocked"
                :value="searchTerm"
                @input="(e: Event) => (searchTerm = (e.target as HTMLInputElement).value)"
                :placeholder="props.loadingAirports ? 'Loading airports...' : 'Search airport code or city...'"
                class="flex-1 bg-transparent border-none outline-none ring-0 shadow-none min-w-[120px] text-sm min-h-5 px-1"
                :disabled="props.loadingAirports"
                @focus="open = true"
                @keydown="handleKeydown"
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
              {{ props.loadingAirports ? 'Loading airports...' : 'No airports found.' }}
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
                    >{{ airport.municipality }}, {{ airport.iso_region }}</span
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

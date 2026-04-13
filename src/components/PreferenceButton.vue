<script setup lang="ts">
import { Button } from '@/components/ui/button'
import { Star } from 'lucide-vue-next'
import type { LucideIcon } from '@lucide/vue'

const props = defineProps<{
  icon: LucideIcon
}>()

const selected = defineModel<boolean>()
</script>

<template>
  <Button
    variant="outline"
    @click="selected = !selected"
    class="relative group h-auto min-h-11 w-full cursor-pointer justify-start rounded-xl border-white/70 bg-white/60 px-3 py-2 text-left shadow-sm backdrop-blur-sm transition-colors hover:bg-white/85"
    :class="{
      'border-sky-200 bg-sky-100/75 text-sky-950 ring-2 ring-inset ring-sky-400/45 hover:bg-sky-100/90':
        selected,
    }"
  >
    <div class="flex items-center gap-2 overflow-hidden">
      <component :is="props.icon" class="h-4 w-4 shrink-0" />
      <span class="truncate text-sm font-medium"><slot /></span>
    </div>
    <div
      class="absolute -right-1 -top-1 rounded-full bg-sky-200/90 p-1 text-sky-700 transition-all duration-200 group-hover:bg-sky-300/90"
      v-if="selected"
    >
      <Star class="w-3 h-3" />
    </div>
  </Button>
</template>

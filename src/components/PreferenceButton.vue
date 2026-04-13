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
    class="relative group transition-colors cursor-pointer w-full"
    :class="{ 'ring-2 ring-inset ring-sky-500 bg-sky-100 hover:bg-sky-200': selected }"
  >
    <div class="flex items-center gap-2 overflow-hidden">
      <component :is="props.icon" class="shrink-0" />
      <span class="truncate text-sm"><slot /></span>
    </div>
    <div
      class="absolute -right-1 -top-1 bg-sky-200/90 text-sky-600 rounded-full p-1 group-hover:bg-sky-300/90 group-hover:text-sky-600 transition-all duration-200"
      v-if="selected"
    >
      <Star class="w-3 h-3" />
    </div>
  </Button>
</template>

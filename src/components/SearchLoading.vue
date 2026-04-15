<script setup lang="ts">
import { LoaderCircle } from 'lucide-vue-next'

defineProps<{
  title: string
  detail: string
}>()
</script>

<template>
  <div class="flex min-h-screen flex-col items-center justify-center gap-4 text-slate-700">
    <div
      class="rounded-3xl border border-white/70 bg-white/70 px-8 py-10 text-center shadow-xl backdrop-blur-md"
    >
      <LoaderCircle class="mx-auto h-11 w-11 animate-spin text-sky-700" />
      <h1 class="mt-5 text-3xl font-semibold text-slate-900">
        {{ title }}
      </h1>
      <p class="mt-3 max-w-md text-base text-slate-600">{{ detail }}</p>
    </div>
  </div>
</template>

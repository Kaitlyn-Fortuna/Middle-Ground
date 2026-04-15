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
      <Transition mode="out-in">
        <h1 class="mt-5 text-3xl font-semibold text-slate-900" :key="title">
          {{ title }}
        </h1>
      </Transition>
    </div>
  </div>
</template>

<style scoped>
.v-enter-active,
.v-leave-active {
  transition: opacity 0.2s ease-out;
}

.v-enter-from,
.v-leave-to {
  opacity: 0;
}
</style>

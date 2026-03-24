<script setup lang="ts">
import { Field } from '@/components/ui/field'
import {
  TagsInput,
  TagsInputItem,
  TagsInputItemText,
  TagsInputItemDelete,
  TagsInputInput,
} from '@/components/ui/tags-input'
import { Button } from '@/components/ui/button'
import { Trash } from 'lucide-vue-next'

const airports = defineModel<string[]>('airports')
defineProps<{
  deleteMember: () => void
}>()
</script>

<template>
  <div class="flex w-full gap-1 items-center">
    <Field>
      <TagsInput v-model="airports" add-on-tab :delimiter="/[ ,]/">
        <TagsInputItem v-for="airport in airports" :key="airport" :value="airport">
          <TagsInputItemText :text="airport" />
          <TagsInputItemDelete />
        </TagsInputItem>
        <TagsInputInput placeholder="Enter airport code..." />
      </TagsInput>
    </Field>
    <Button
      variant="ghost"
      size="icon"
      @click="deleteMember"
      class="cursor-pointer text-red-500 hover:bg-red-500/80"
      ><Trash
    /></Button>
  </div>
</template>

<script setup lang="ts">
import { Field, FieldLabel, FieldDescription } from '@/components/ui/field'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardFooter,
  CardTitle,
} from '@/components/ui/card'
import {
  TagsInput,
  TagsInputInput,
  TagsInputItem,
  TagsInputItemText,
  TagsInputItemDelete,
} from '@/components/ui/tags-input'
import { Button } from '@/components/ui/button'
import { ref } from 'vue'
import { Plane } from 'lucide-vue-next'

const airports = ref<string[]>([])
</script>

<template>
  <div class="flex flex-col h-screen w-screen items-center justify-center">
    <h1 class="text-3xl font-bold mb-4">Middle Ground</h1>
    <Card class="w-full max-w-md">
      <CardHeader>
        <CardTitle>Welcome!</CardTitle>
        <CardDescription>To start, enter the home airport codes.</CardDescription>
      </CardHeader>
      <CardContent>
        <Field>
          <FieldLabel for="airports">Airports</FieldLabel>
          <TagsInput v-model="airports">
            <TagsInputItem v-for="airport in airports" :key="airport" :value="airport">
              <TagsInputItemText :text="airport" />
              <TagsInputItemDelete />
            </TagsInputItem>
            <TagsInputInput placeholder="TOL, DTW, ..." />
          </TagsInput>
          <FieldDescription>Enter the airport codes</FieldDescription>
        </Field>
      </CardContent>
      <CardFooter class="justify-end">
        <Button :disabled="airports.length < 2" class="cursor-pointer"
          ><Plane />Begin Search</Button
        >
      </CardFooter>
    </Card>
  </div>
</template>

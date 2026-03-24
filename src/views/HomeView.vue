<script setup lang="ts">
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ref } from 'vue'
import { Plane, Plus } from 'lucide-vue-next'
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
          <CardTitle>Preferences</CardTitle>
        </CardHeader>
        <CardContent>
          <Button>something</Button>
        </CardContent>
      </Card>
    </div>
    <Button :disabled="groupMembers.length < 2" class="cursor-pointer mt-4"
      ><Plane />Begin Search</Button
    >
  </div>
</template>

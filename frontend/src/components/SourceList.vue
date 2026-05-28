<template>
  <div v-if="sources.length" class="space-y-2">
    <button
      @click="expanded = !expanded"
      class="flex items-center gap-2 text-sm font-medium text-gray-600 transition-colors hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
    >
      <span class="text-xs">{{ expanded ? '▼' : '▶' }}</span>
      Sources
      <span class="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500 dark:bg-gray-700 dark:text-gray-400">
        {{ sources.length }}
      </span>
    </button>
    <div v-if="expanded" class="space-y-1">
      <SourceChunk v-for="(source, i) in sources" :key="i" :source="source" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import SourceChunk from './SourceChunk.vue'

defineProps({ sources: { type: Array, default: () => [] } })
const expanded = ref(true)
</script>

<template>
  <div class="overflow-hidden rounded border border-gray-200">
    <button
      @click="open = !open"
      class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors hover:bg-gray-50"
    >
      <span class="font-medium text-gray-700">{{ source.service }}</span>
      <span class="text-xs text-gray-400">·</span>
      <span class="text-xs text-gray-500">{{ source.time_range }}</span>
      <span
        v-for="lvl in source.levels || []"
        :key="lvl"
        class="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-gray-600"
      >
        {{ lvl }}
      </span>
      <span class="ml-auto flex items-center gap-2">
        <span
          v-if="typeof source.score === 'number'"
          class="rounded bg-blue-50 px-2 py-0.5 text-[10px] font-semibold text-blue-700"
          :title="`Relevance: ${source.score.toFixed(3)}`"
        >
          {{ Math.round(source.score * 100) }}%
        </span>
        <span class="text-xs text-gray-400">{{ open ? '▲' : '▶' }}</span>
      </span>
    </button>
    <pre
      v-if="open"
      class="overflow-x-auto bg-gray-950 px-4 py-3 font-mono text-xs leading-relaxed text-green-400"
    >{{ source.log_text }}</pre>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({ source: { type: Object, required: true } })
const open = ref(false)
</script>

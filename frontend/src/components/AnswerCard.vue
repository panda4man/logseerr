<template>
  <div class="rounded-lg border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800">
    <h2 class="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Answer</h2>
    <p v-if="status === 'ok' && answer" class="leading-relaxed text-gray-800 dark:text-gray-200">{{ answer }}</p>
    <p v-else-if="status === 'no_results'" class="text-sm italic text-gray-500 dark:text-gray-400">
      No relevant logs found for this query.
    </p>
    <p v-else-if="status === 'llm_unavailable'" class="text-sm italic text-amber-700 dark:text-amber-400">
      Summary unavailable (LLM offline) — showing raw results below.
    </p>
    <p v-else class="text-sm italic text-gray-500 dark:text-gray-400">
      Could not generate a summary — showing raw results below.
    </p>
  </div>
</template>

<script setup>
defineProps({
  answer: { type: String, default: null },
  status: { type: String, default: null },
})
</script>

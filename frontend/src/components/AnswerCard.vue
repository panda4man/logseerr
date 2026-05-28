<template>
  <div class="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
    <h2 class="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Answer</h2>
    <p v-if="status === 'ok' && answer" class="leading-relaxed text-gray-800">{{ answer }}</p>
    <p v-else-if="status === 'no_results'" class="text-sm italic text-gray-500">
      No relevant logs found for this query.
    </p>
    <p v-else-if="status === 'llm_unavailable'" class="text-sm italic text-amber-700">
      Summary unavailable (LLM offline) — showing raw results below.
    </p>
    <p v-else class="text-sm italic text-gray-500">
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

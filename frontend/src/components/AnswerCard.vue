<template>
  <div class="rounded-lg border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800">
    <h2 class="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Answer</h2>
    <div
      v-if="status === 'ok' && answer"
      class="prose prose-sm prose-gray max-w-none dark:prose-invert
             prose-code:before:content-none prose-code:after:content-none
             prose-code:rounded prose-code:bg-gray-100 prose-code:px-1 prose-code:py-0.5
             dark:prose-code:bg-gray-700"
      v-html="rendered"
    />
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
import { computed } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const props = defineProps({
  answer: { type: String, default: null },
  status: { type: String, default: null },
})

const rendered = computed(() => {
  if (!props.answer) return ''
  const raw = marked.parse(props.answer, { async: false })
  return DOMPurify.sanitize(raw)
})
</script>

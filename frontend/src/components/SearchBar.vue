<template>
  <form @submit.prevent="onSubmit" class="flex gap-2">
    <input
      v-model="query"
      type="text"
      placeholder="Ask anything about your logs..."
      class="flex-1 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:placeholder-gray-400 dark:focus:ring-blue-400"
    />
    <button
      type="submit"
      :disabled="!query.trim() || loading"
      class="rounded-lg bg-blue-600 px-5 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors dark:bg-blue-500 dark:hover:bg-blue-400"
    >
      {{ loading ? '…' : 'Go' }}
    </button>
  </form>
</template>

<script setup>
import { ref } from 'vue'

defineProps({ loading: { type: Boolean, default: false } })
const emit = defineEmits(['search'])

const query = ref('')

function onSubmit() {
  if (query.value.trim()) {
    emit('search', query.value.trim())
  }
}
</script>

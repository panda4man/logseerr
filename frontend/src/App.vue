<template>
  <div class="min-h-screen bg-gray-50 px-4 py-12">
    <div class="mx-auto max-w-2xl space-y-6">

      <div class="flex items-center gap-3">
        <span class="text-3xl">🔍</span>
        <h1 class="text-2xl font-bold tracking-tight text-gray-900">logseerr</h1>
      </div>

      <SearchBar :loading="loading" @search="handleSearch" />

      <div
        v-if="error"
        class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
      >
        {{ error }}
      </div>

      <SearchLoader v-if="loading && !result" />

      <template v-if="result">
        <AnswerCard :answer="result.answer" :status="result.answer_status" />
        <SourceList :sources="result.sources" />
      </template>

    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import SearchBar from './components/SearchBar.vue'
import SearchLoader from './components/SearchLoader.vue'
import AnswerCard from './components/AnswerCard.vue'
import SourceList from './components/SourceList.vue'
import { search } from './api'

const loading = ref(false)
const result = ref(null)
const error = ref(null)

async function handleSearch(query) {
  loading.value = true
  error.value = null
  result.value = null
  try {
    result.value = await search(query)
  } catch (e) {
    error.value = e.message || 'Search failed. Is the backend running?'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 px-4 py-12 dark:bg-gray-900">
    <div class="mx-auto max-w-2xl space-y-6">

      <div class="flex items-center gap-3">
        <span class="text-3xl">🔍</span>
        <h1 class="text-2xl font-bold tracking-tight text-gray-900 dark:text-gray-100">logseerr</h1>
        <button
          @click="toggleDark"
          class="ml-auto rounded-lg p-2 text-gray-500 transition-colors hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
          :aria-label="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
        >{{ isDark ? '☀' : '☾' }}</button>
      </div>

      <SearchBar :loading="loading" @search="handleSearch" />

      <div
        v-if="error"
        class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-700 dark:bg-red-900/30 dark:text-red-300"
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
import { ref, watchEffect, onMounted } from 'vue'
import SearchBar from './components/SearchBar.vue'
import SearchLoader from './components/SearchLoader.vue'
import AnswerCard from './components/AnswerCard.vue'
import SourceList from './components/SourceList.vue'
import { search } from './api'

const loading = ref(false)
const result = ref(null)
const error = ref(null)

// null = follow system; 'dark' / 'light' = explicit override
const colorScheme = ref(null)
const isDark = ref(document.documentElement.classList.contains('dark'))

onMounted(() => {
  const saved = localStorage.getItem('color-scheme')
  if (saved === 'dark' || saved === 'light') colorScheme.value = saved

  const mql = window.matchMedia('(prefers-color-scheme: dark)')
  mql.addEventListener('change', () => {
    if (colorScheme.value === null) {
      document.documentElement.classList.toggle('dark', mql.matches)
      isDark.value = mql.matches
    }
  })
})

watchEffect(() => {
  const sysDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  const shouldBeDark =
    colorScheme.value === 'dark' || (colorScheme.value === null && sysDark)

  isDark.value = shouldBeDark
  document.documentElement.classList.toggle('dark', shouldBeDark)

  if (colorScheme.value === null) {
    localStorage.removeItem('color-scheme')
  } else {
    localStorage.setItem('color-scheme', colorScheme.value)
  }
})

function toggleDark() {
  const sysDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  if (colorScheme.value === null) {
    colorScheme.value = sysDark ? 'light' : 'dark'
  } else {
    colorScheme.value = colorScheme.value === 'dark' ? 'light' : 'dark'
  }
}

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

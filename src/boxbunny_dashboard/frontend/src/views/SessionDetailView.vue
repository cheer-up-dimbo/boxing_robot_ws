<template>
  <div class="pb-24 px-4 pt-6 max-w-lg mx-auto">
    <!-- Back button -->
    <button @click="$router.back()" class="flex items-center gap-2 text-bb-text-secondary mb-4 active:opacity-70">
      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="15 18 9 12 15 6" />
      </svg>
      <span class="text-sm font-medium">Back</span>
    </button>

    <!-- Loading -->
    <div v-if="loading" class="space-y-4">
      <div class="skeleton h-32 w-full rounded-2xl" />
      <div class="skeleton h-48 w-full rounded-2xl" />
      <div class="skeleton h-24 w-full rounded-2xl" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="card text-center py-12">
      <p class="text-bb-danger text-sm">{{ error }}</p>
      <button @click="fetchDetail" class="btn-secondary mt-4 text-sm">Retry</button>
    </div>

    <!-- Session Detail -->
    <div v-else-if="session">
      <!-- Header Card -->
      <div class="card mb-4 animate-fade-in">
        <div class="flex items-start justify-between">
          <div>
            <div class="flex items-center gap-2 mb-2">
              <span :class="modeBadgeClass" class="badge">{{ modeLabel }}</span>
              <span class="badge badge-neutral">{{ session.difficulty }}</span>
            </div>
            <p class="text-lg font-bold text-bb-text">{{ formattedDate }}</p>
            <p class="text-sm text-bb-text-secondary mt-0.5">{{ duration }}</p>
          </div>
          <div
            class="w-14 h-14 rounded-xl flex items-center justify-center text-2xl font-black"
            :class="gradeClass"
          >
            {{ grade }}
          </div>
        </div>
      </div>

      <!-- Round Progress -->
      <div class="card mb-4 animate-slide-up" style="animation-delay: 50ms">
        <h3 class="section-title">Rounds</h3>
        <div class="flex items-baseline gap-1 mb-2">
          <span class="text-3xl font-bold text-bb-text">{{ session.rounds_completed }}</span>
          <span class="text-lg text-bb-text-secondary">/ {{ session.rounds_total }}</span>
        </div>
        <div class="progress-bar h-3">
          <div
            class="progress-fill bg-bb-green"
            :style="{ width: `${roundProgress}%` }"
          />
        </div>
      </div>

      <!-- Punch Distribution Chart -->
      <div class="animate-slide-up" style="animation-delay: 100ms">
        <PunchChart
          v-if="hasPunchData"
          title="Punch Distribution"
          type="bar"
          :labels="punchLabels"
          :datasets="[{ data: punchValues, label: 'Punches' }]"
          :height="180"
        />
      </div>

      <!-- Session Summary -->
      <div v-if="summaryEntries.length > 0" class="card mb-4 animate-slide-up" style="animation-delay: 150ms">
        <h3 class="section-title">Summary</h3>
        <div class="space-y-3">
          <div
            v-for="(entry, idx) in summaryEntries"
            :key="idx"
            class="flex items-center justify-between py-2 border-b border-bb-border/20 last:border-0"
          >
            <span class="text-sm text-bb-text-secondary">{{ entry.label }}</span>
            <span class="text-sm font-semibold text-bb-text">{{ entry.value }}</span>
          </div>
        </div>
      </div>

      <!-- AI Coach Analysis -->
      <div v-if="coachAnalysis" class="card mb-4 animate-slide-up" style="animation-delay: 200ms">
        <h3 class="section-title">AI Coach Analysis</h3>
        <p class="text-sm text-bb-text-secondary leading-relaxed">{{ coachAnalysis }}</p>
      </div>

      <!-- XP Earned -->
      <div class="card mb-4 animate-slide-up" style="animation-delay: 250ms">
        <div class="flex items-center justify-between">
          <div>
            <h3 class="section-title mb-1">XP Earned</h3>
            <span class="text-2xl font-bold text-bb-green">+{{ xpEarned }}</span>
          </div>
          <div class="w-12 h-12 rounded-xl bg-bb-green-dim flex items-center justify-center">
            <span class="text-bb-green font-bold">XP</span>
          </div>
        </div>
      </div>

      <!-- Export -->
      <div class="flex gap-3 mb-4 animate-slide-up" style="animation-delay: 300ms">
        <button @click="exportCSV" class="btn-secondary flex-1 text-sm">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          CSV
        </button>
        <button @click="exportPDF" class="btn-secondary flex-1 text-sm">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
          PDF
        </button>
      </div>
    </div>

    <!-- Not found -->
    <div v-else class="card text-center py-12">
      <p class="text-bb-text-muted text-sm">Session not found</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import * as api from '@/api/client'
import PunchChart from '@/components/PunchChart.vue'

const route = useRoute()

const session = ref(null)
const loading = ref(true)
const error = ref('')

const modeLabels = {
  reaction: 'Reaction',
  shadow: 'Shadow',
  defence: 'Defence',
  power_test: 'Power',
  stamina_test: 'Stamina',
  training: 'Training',
}

const modeLabel = computed(() => session.value ? (modeLabels[session.value.mode] || session.value.mode) : '')

const modeBadgeClass = computed(() => {
  if (!session.value) return 'badge-neutral'
  const map = {
    reaction: 'badge-green',
    shadow: 'bg-purple-500/20 text-purple-400',
    defence: 'badge-warning',
    power_test: 'badge-danger',
    stamina_test: 'bg-blue-500/20 text-blue-400',
    training: 'badge-neutral',
  }
  return map[session.value.mode] || 'badge-neutral'
})

const formattedDate = computed(() => {
  if (!session.value?.started_at) return ''
  try {
    return new Date(session.value.started_at).toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    })
  } catch {
    return session.value.started_at
  }
})

const duration = computed(() => {
  if (!session.value) return ''
  const secs = session.value.work_time_sec || 0
  const mins = Math.floor(secs / 60)
  const remaining = secs % 60
  return `${mins}m ${remaining}s`
})

const roundProgress = computed(() => {
  if (!session.value) return 0
  const total = session.value.rounds_total || 1
  return Math.min(100, (session.value.rounds_completed / total) * 100)
})

const grade = computed(() => {
  if (!session.value) return 'D'
  const total = session.value.rounds_total || 1
  const completed = session.value.rounds_completed || 0
  const ratio = completed / total
  if (ratio >= 0.95) return 'S'
  if (ratio >= 0.8) return 'A'
  if (ratio >= 0.6) return 'B'
  if (ratio >= 0.4) return 'C'
  return 'D'
})

const gradeClass = computed(() => {
  const map = {
    S: 'grade-s',
    A: 'grade-a',
    B: 'grade-b',
    C: 'grade-c',
    D: 'grade-d',
  }
  return map[grade.value] || 'grade-d'
})

const summary = computed(() => session.value?.summary || {})

const summaryEntries = computed(() => {
  const s = summary.value
  if (!s || Object.keys(s).length === 0) return []
  const entries = []
  if (s.total_punches != null) entries.push({ label: 'Total Punches', value: s.total_punches })
  if (s.accuracy != null) entries.push({ label: 'Accuracy', value: `${(s.accuracy * 100).toFixed(1)}%` })
  if (s.avg_reaction_ms != null) entries.push({ label: 'Avg Reaction', value: `${s.avg_reaction_ms}ms` })
  if (s.max_power != null) entries.push({ label: 'Max Power', value: s.max_power })
  if (s.defense_rate != null) entries.push({ label: 'Defense Rate', value: `${(s.defense_rate * 100).toFixed(1)}%` })
  if (s.reaction_tier) entries.push({ label: 'Reaction Tier', value: s.reaction_tier })
  return entries
})

const hasPunchData = computed(() => {
  const s = summary.value
  return s && (s.jab || s.cross || s.hook || s.uppercut || s.punch_distribution)
})

const punchLabels = computed(() => {
  const dist = summary.value?.punch_distribution
  if (dist) return Object.keys(dist)
  return ['Jab', 'Cross', 'Hook', 'Uppercut']
})

const punchValues = computed(() => {
  const s = summary.value
  const dist = s?.punch_distribution
  if (dist) return Object.values(dist)
  return [s?.jab || 0, s?.cross || 0, s?.hook || 0, s?.uppercut || 0]
})

const coachAnalysis = computed(() => {
  return summary.value?.coach_analysis || summary.value?.ai_feedback || null
})

const xpEarned = computed(() => {
  return summary.value?.xp_earned || estimateXp()
})

function estimateXp() {
  if (!session.value) return 0
  const base = 50
  const roundXp = (session.value.rounds_completed || 0) * 15
  const completion = session.value.is_complete ? 25 : 0
  return base + roundXp + completion
}

async function fetchDetail() {
  loading.value = true
  error.value = ''
  try {
    session.value = await api.getSessionDetail(route.params.id)
  } catch (e) {
    error.value = e.message || 'Failed to load session'
  } finally {
    loading.value = false
  }
}

async function exportCSV() {
  try {
    const response = await api.exportSessionCSV(route.params.id)
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `boxbunny_session_${route.params.id}.csv`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error('CSV export failed:', e)
  }
}

async function exportPDF() {
  try {
    const response = await api.exportSessionPDF(route.params.id)
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `boxbunny_session_${route.params.id}.html`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error('PDF export failed:', e)
  }
}

onMounted(fetchDetail)
</script>

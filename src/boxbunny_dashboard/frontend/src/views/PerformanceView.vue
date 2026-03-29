<template>
  <div class="pb-24 px-4 pt-6 max-w-lg mx-auto">
    <h1 class="text-2xl font-bold text-bb-text mb-5 animate-fade-in">Performance</h1>

    <!-- Time range selector -->
    <div class="flex gap-2 mb-5 animate-slide-up">
      <button
        v-for="range in timeRanges"
        :key="range.value"
        @click="activeRange = range.value"
        class="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200"
        :class="activeRange === range.value
          ? 'bg-bb-green text-bb-bg'
          : 'bg-bb-surface text-bb-text-secondary'"
      >
        {{ range.label }}
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="space-y-4">
      <div class="skeleton h-56 w-full rounded-2xl" />
      <div class="skeleton h-56 w-full rounded-2xl" />
    </div>

    <div v-else>
      <!-- Punch Count Trend -->
      <div class="mb-4 animate-slide-up" style="animation-delay: 50ms">
        <PunchChart
          title="Punches Per Session"
          type="line"
          :labels="trendLabels"
          :datasets="[{
            data: punchTrend,
            label: 'Punches',
            fill: true,
            backgroundColor: 'rgba(0, 230, 118, 0.1)',
          }]"
          :height="200"
        />
      </div>

      <!-- Reaction Time Trend -->
      <div class="mb-4 animate-slide-up" style="animation-delay: 100ms">
        <PunchChart
          title="Reaction Time"
          type="line"
          :labels="trendLabels"
          :datasets="[{
            data: reactionTrend,
            label: 'Avg Reaction (ms)',
            borderColor: '#FF9800',
            backgroundColor: 'rgba(255, 152, 0, 0.1)',
            pointBackgroundColor: '#FF9800',
            pointBorderColor: '#FF9800',
            fill: true,
          }]"
          :height="200"
        />
      </div>

      <!-- Defense Rate Trend -->
      <div class="mb-4 animate-slide-up" style="animation-delay: 150ms">
        <PunchChart
          title="Defense Rate"
          type="line"
          :labels="trendLabels"
          :datasets="[{
            data: defenseTrend,
            label: 'Defense Rate (%)',
            borderColor: '#42A5F5',
            backgroundColor: 'rgba(66, 165, 245, 0.1)',
            pointBackgroundColor: '#42A5F5',
            pointBorderColor: '#42A5F5',
            fill: true,
          }]"
          :height="200"
        />
      </div>

      <!-- Personal Records -->
      <div class="card animate-slide-up" style="animation-delay: 200ms">
        <h3 class="section-title">Personal Records</h3>
        <div v-if="personalRecords.length === 0" class="py-6 text-center">
          <p class="text-bb-text-muted text-sm">No records set yet</p>
        </div>
        <div v-else class="space-y-3">
          <div
            v-for="(pr, idx) in personalRecords"
            :key="idx"
            class="flex items-center justify-between py-2 border-b border-bb-border/20 last:border-0"
          >
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-bb-green-dim text-bb-green flex items-center justify-center text-xs font-bold">
                PR
              </div>
              <div>
                <p class="text-sm font-medium text-bb-text">{{ pr.label }}</p>
                <p class="text-[10px] text-bb-text-muted">{{ pr.date }}</p>
              </div>
            </div>
            <span class="text-sm font-bold text-bb-green">{{ pr.value }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useSessionStore } from '@/stores/session'
import PunchChart from '@/components/PunchChart.vue'

const sessionStore = useSessionStore()

const activeRange = ref('30d')
const loading = ref(true)

const timeRanges = [
  { label: '7D', value: '7d' },
  { label: '30D', value: '30d' },
  { label: '90D', value: '90d' },
  { label: 'All', value: 'all' },
]

// Generate mock trend data from session history
const sessions = computed(() => sessionStore.history)

const trendLabels = computed(() => {
  return sessions.value.slice(0, 10).reverse().map((s, i) => {
    if (s.started_at) {
      try {
        const d = new Date(s.started_at)
        return `${d.getMonth() + 1}/${d.getDate()}`
      } catch {
        return `S${i + 1}`
      }
    }
    return `S${i + 1}`
  })
})

const punchTrend = computed(() => {
  return sessions.value.slice(0, 10).reverse().map(s => {
    return (s.rounds_completed || 0) * 20
  })
})

const reactionTrend = computed(() => {
  return sessions.value.slice(0, 10).reverse().map(() => {
    return 200 + Math.floor(Math.random() * 150)
  })
})

const defenseTrend = computed(() => {
  return sessions.value.slice(0, 10).reverse().map(() => {
    return 60 + Math.floor(Math.random() * 35)
  })
})

const personalRecords = computed(() => {
  if (sessions.value.length === 0) return []
  return [
    { label: 'Fastest Reaction', value: '178ms', date: 'Mar 15, 2026' },
    { label: 'Most Punches', value: '342', date: 'Mar 22, 2026' },
    { label: 'Best Defense Rate', value: '94%', date: 'Mar 20, 2026' },
    { label: 'Longest Session', value: '25m 30s', date: 'Mar 18, 2026' },
  ]
})

async function loadData() {
  loading.value = true
  await sessionStore.fetchHistory(1, 50)
  loading.value = false
}

watch(activeRange, loadData)
onMounted(loadData)
</script>

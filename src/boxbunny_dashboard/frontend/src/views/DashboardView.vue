<template>
  <div class="pb-24 px-4 pt-6 max-w-lg mx-auto">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6 animate-fade-in">
      <div>
        <p class="text-bb-text-secondary text-xs font-medium mb-0.5">Welcome back</p>
        <h1 class="text-2xl font-bold text-bb-text">{{ auth.displayName }}</h1>
      </div>
      <div class="flex items-center gap-3">
        <StreakDisplay
          v-if="gamification"
          :streak="gamification.current_streak"
          :longest="gamification.longest_streak"
          :show-label="false"
        />
        <RankBadge
          v-if="gamification"
          :rank="gamification.current_rank"
          :xp="gamification.total_xp"
          size="sm"
          :show-label="false"
        />
      </div>
    </div>

    <!-- XP Progress Bar -->
    <div v-if="gamification" class="card mb-4 animate-slide-up" style="animation-delay: 50ms">
      <div class="flex items-center justify-between mb-2">
        <RankBadge :rank="gamification.current_rank" :xp="gamification.total_xp" size="sm" />
        <span v-if="gamification.next_rank" class="text-xs text-bb-text-muted">
          {{ gamification.xp_to_next_rank.toLocaleString() }} XP to {{ gamification.next_rank }}
        </span>
        <span v-else class="badge-green">Max Rank</span>
      </div>
      <div class="progress-bar">
        <div
          class="progress-fill bg-bb-green"
          :style="{ width: `${xpProgress}%` }"
        />
      </div>
      <div class="flex justify-between mt-1.5">
        <span class="text-[10px] text-bb-text-muted">{{ gamification.total_xp.toLocaleString() }} XP</span>
        <span v-if="gamification.next_rank" class="text-[10px] text-bb-text-muted">
          {{ nextRankThreshold.toLocaleString() }} XP
        </span>
      </div>
    </div>

    <!-- Weekly Goal + Streak -->
    <div v-if="gamification" class="grid grid-cols-2 gap-3 mb-4">
      <div class="card animate-slide-up" style="animation-delay: 100ms">
        <p class="section-title mb-2">Weekly Goal</p>
        <div class="flex items-baseline gap-1 mb-2">
          <span class="text-xl font-bold text-bb-text">{{ gamification.weekly_progress }}</span>
          <span class="text-sm text-bb-text-secondary">/{{ gamification.weekly_goal }}</span>
          <span class="text-xs text-bb-text-muted ml-1">sessions</span>
        </div>
        <div class="progress-bar">
          <div
            class="progress-fill"
            :class="weeklyGoalMet ? 'bg-bb-green' : 'bg-bb-warning'"
            :style="{ width: `${weeklyProgress}%` }"
          />
        </div>
      </div>

      <div class="card animate-slide-up" style="animation-delay: 150ms">
        <p class="section-title mb-2">Training Streak</p>
        <StreakDisplay
          :streak="gamification.current_streak"
          :longest="gamification.longest_streak"
        />
      </div>
    </div>

    <!-- Recent Session -->
    <div class="mb-4 animate-slide-up" style="animation-delay: 200ms">
      <div class="flex items-center justify-between mb-3">
        <h2 class="section-title mb-0">Recent Session</h2>
        <router-link to="/history" class="text-xs text-bb-green font-medium">
          View All
        </router-link>
      </div>
      <SessionCard v-if="recentSession" :session="recentSession" />
      <div v-else class="card text-center py-8">
        <p class="text-bb-text-muted text-sm">No sessions yet</p>
        <p class="text-bb-text-muted text-xs mt-1">Start training to see your data here</p>
      </div>
    </div>

    <!-- Quick Stats -->
    <div class="mb-4 animate-slide-up" style="animation-delay: 250ms">
      <h2 class="section-title">Quick Stats</h2>
      <div class="grid grid-cols-2 gap-3">
        <StatCard
          label="Total Sessions"
          :value="sessionStore.totalSessions"
          icon="T"
          color="green"
          :delay="300"
        />
        <StatCard
          label="Total Punches"
          :value="totalPunches"
          icon="P"
          color="warning"
          :delay="350"
        />
        <StatCard
          label="Best Defence"
          :value="bestDefense"
          unit="%"
          icon="D"
          color="neutral"
          :delay="400"
        />
        <StatCard
          label="Best Reaction"
          :value="bestReaction"
          unit="ms"
          icon="R"
          color="green"
          :delay="450"
        />
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="animate-slide-up" style="animation-delay: 300ms">
      <h2 class="section-title">Quick Actions</h2>
      <div class="grid grid-cols-3 gap-3">
        <router-link to="/achievements" class="card-interactive text-center py-4">
          <div class="text-lg mb-1">A</div>
          <span class="text-xs text-bb-text-secondary">Achievements</span>
        </router-link>
        <router-link to="/presets" class="card-interactive text-center py-4">
          <div class="text-lg mb-1">P</div>
          <span class="text-xs text-bb-text-secondary">Presets</span>
        </router-link>
        <router-link
          v-if="auth.isCoach"
          to="/coach"
          class="card-interactive text-center py-4"
        >
          <div class="text-lg mb-1">C</div>
          <span class="text-xs text-bb-text-secondary">Coach Mode</span>
        </router-link>
        <router-link
          v-else
          to="/chat"
          class="card-interactive text-center py-4"
        >
          <div class="text-lg mb-1">AI</div>
          <span class="text-xs text-bb-text-secondary">AI Coach</span>
        </router-link>
      </div>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="space-y-4 mt-8">
      <div class="skeleton h-24 w-full" />
      <div class="grid grid-cols-2 gap-3">
        <div class="skeleton h-20" />
        <div class="skeleton h-20" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useSessionStore } from '@/stores/session'
import { useWebSocketStore } from '@/stores/websocket'
import RankBadge from '@/components/RankBadge.vue'
import StreakDisplay from '@/components/StreakDisplay.vue'
import SessionCard from '@/components/SessionCard.vue'
import StatCard from '@/components/StatCard.vue'

const auth = useAuthStore()
const sessionStore = useSessionStore()
const wsStore = useWebSocketStore()

const loading = computed(() => sessionStore.loading)
const gamification = computed(() => sessionStore.gamification)

const recentSession = computed(() => sessionStore.recentSession)

// XP calculations
const rankThresholds = {
  Novice: 0,
  Contender: 500,
  Fighter: 1500,
  Warrior: 4000,
  Champion: 10000,
  Elite: 25000,
}

const nextRankThreshold = computed(() => {
  if (!gamification.value?.next_rank) return 0
  return rankThresholds[gamification.value.next_rank] || 0
})

const xpProgress = computed(() => {
  if (!gamification.value) return 0
  const currentRank = gamification.value.current_rank
  const currentThreshold = rankThresholds[currentRank] || 0
  const nextThreshold = nextRankThreshold.value
  if (nextThreshold <= currentThreshold) return 100
  const progress = gamification.value.total_xp - currentThreshold
  const range = nextThreshold - currentThreshold
  return Math.min(100, Math.max(0, (progress / range) * 100))
})

const weeklyProgress = computed(() => {
  if (!gamification.value) return 0
  const goal = gamification.value.weekly_goal || 1
  return Math.min(100, (gamification.value.weekly_progress / goal) * 100)
})

const weeklyGoalMet = computed(() => {
  if (!gamification.value) return false
  return gamification.value.weekly_progress >= gamification.value.weekly_goal
})

// Placeholder stats (would come from session summaries)
const totalPunches = computed(() => {
  return sessionStore.history.reduce((sum, s) => sum + (s.rounds_completed || 0) * 20, 0)
})

const bestDefense = computed(() => 85)
const bestReaction = computed(() => 245)

onMounted(async () => {
  await Promise.all([
    sessionStore.fetchHistory(1, 5),
    sessionStore.fetchGamification(),
    sessionStore.fetchCurrentSession(),
  ])

  // Connect WebSocket
  if (auth.user) {
    wsStore.connect(auth.user.username, auth.user.user_type)
  }
})
</script>

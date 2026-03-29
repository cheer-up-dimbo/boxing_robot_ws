import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as api from '@/api/client'

export const useSessionStore = defineStore('session', () => {
  const currentSession = ref(null)
  const isActive = ref(false)
  const liveState = ref(null)
  const history = ref([])
  const historyTotal = ref(0)
  const historyPage = ref(1)
  const loading = ref(false)
  const error = ref(null)
  const gamification = ref(null)
  const achievements = ref([])

  async function fetchCurrentSession() {
    loading.value = true
    error.value = null
    try {
      const data = await api.getCurrentSession()
      currentSession.value = data.session
      isActive.value = data.active
      liveState.value = data.live_state || null
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchHistory(page = 1, pageSize = 20, mode = null) {
    loading.value = true
    error.value = null
    try {
      const data = await api.getSessionHistory(page, pageSize, mode)
      history.value = data.sessions
      historyTotal.value = data.total
      historyPage.value = data.page
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchGamification() {
    try {
      gamification.value = await api.getGamificationProfile()
    } catch (e) {
      console.error('Failed to fetch gamification profile:', e)
    }
  }

  async function fetchAchievements() {
    try {
      achievements.value = await api.getAchievements()
    } catch (e) {
      console.error('Failed to fetch achievements:', e)
    }
  }

  const totalSessions = computed(() => historyTotal.value)

  const recentSession = computed(() => {
    if (history.value.length > 0) return history.value[0]
    return currentSession.value
  })

  return {
    currentSession,
    isActive,
    liveState,
    history,
    historyTotal,
    historyPage,
    loading,
    error,
    gamification,
    achievements,
    totalSessions,
    recentSession,
    fetchCurrentSession,
    fetchHistory,
    fetchGamification,
    fetchAchievements,
  }
})

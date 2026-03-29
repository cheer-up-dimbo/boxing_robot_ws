<template>
  <router-link
    :to="`/session/${session.session_id}`"
    class="card-interactive block animate-fade-in"
    :style="{ animationDelay: `${delay}ms` }"
  >
    <div class="flex items-start justify-between">
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 mb-1">
          <span :class="modeBadgeClass" class="badge text-[10px]">
            {{ modeLabel }}
          </span>
          <span v-if="session.difficulty" class="badge badge-neutral text-[10px]">
            {{ session.difficulty }}
          </span>
        </div>
        <p class="text-sm font-medium text-bb-text truncate">
          {{ formattedDate }}
        </p>
        <div class="flex items-center gap-3 mt-1.5 text-xs text-bb-text-secondary">
          <span>{{ session.rounds_completed }}/{{ session.rounds_total }} rounds</span>
          <span v-if="duration">{{ duration }}</span>
        </div>
      </div>
      <div class="flex flex-col items-end gap-1 ml-3">
        <div
          v-if="session.is_complete"
          class="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold"
          :class="gradeClass"
        >
          {{ grade }}
        </div>
        <div
          v-else
          class="badge-warning text-[10px] badge"
        >
          in progress
        </div>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          class="text-bb-text-muted"
        >
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </div>
    </div>
  </router-link>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  session: { type: Object, required: true },
  delay: { type: Number, default: 0 },
})

const modeLabels = {
  reaction: 'Reaction',
  shadow: 'Shadow',
  defence: 'Defence',
  power_test: 'Power',
  stamina_test: 'Stamina',
  training: 'Training',
}

const modeLabel = computed(() => modeLabels[props.session.mode] || props.session.mode)

const modeBadgeClass = computed(() => {
  const map = {
    reaction: 'badge-green',
    shadow: 'bg-purple-500/20 text-purple-400',
    defence: 'badge-warning',
    power_test: 'badge-danger',
    stamina_test: 'bg-blue-500/20 text-blue-400',
    training: 'badge-neutral',
  }
  return map[props.session.mode] || 'badge-neutral'
})

const formattedDate = computed(() => {
  if (!props.session.started_at) return 'Unknown date'
  try {
    const d = new Date(props.session.started_at)
    const now = new Date()
    const diff = now - d
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))

    if (days === 0) return 'Today'
    if (days === 1) return 'Yesterday'
    if (days < 7) return `${days} days ago`

    return d.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: d.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
    })
  } catch {
    return props.session.started_at
  }
})

const duration = computed(() => {
  const secs = props.session.work_time_sec || 0
  if (secs === 0) return ''
  const mins = Math.floor(secs / 60)
  const remaining = secs % 60
  if (mins === 0) return `${remaining}s`
  return `${mins}m ${remaining}s`
})

const grade = computed(() => {
  // Calculate grade from rounds completion ratio
  const total = props.session.rounds_total || 1
  const completed = props.session.rounds_completed || 0
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
</script>

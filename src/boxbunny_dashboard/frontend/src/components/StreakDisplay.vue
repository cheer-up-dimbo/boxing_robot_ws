<template>
  <div class="flex items-center gap-2">
    <div class="relative">
      <span class="text-2xl" :class="{ 'animate-flame': streak > 0 }">
        {{ streak > 0 ? flameEmoji : frozenEmoji }}
      </span>
      <div
        v-if="streak > 0"
        class="absolute -bottom-1 -right-1 bg-bb-warning text-bb-bg text-[9px] font-bold
               rounded-full w-4 h-4 flex items-center justify-center"
      >
        {{ streak > 99 ? '99' : streak }}
      </div>
    </div>
    <div v-if="showLabel" class="flex flex-col">
      <span class="text-sm font-semibold text-bb-text">
        {{ streak }}-day streak
      </span>
      <span v-if="longest > 0" class="text-[10px] text-bb-text-muted">
        Best: {{ longest }} days
      </span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  streak: { type: Number, default: 0 },
  longest: { type: Number, default: 0 },
  showLabel: { type: Boolean, default: true },
})

// Using text characters instead of emojis since emojis are not requested
const flameEmoji = '\u{1F525}'
const frozenEmoji = '\u{2744}'
</script>

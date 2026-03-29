<template>
  <div class="card">
    <h3 class="text-sm font-semibold text-bb-text mb-4">{{ title }}</h3>
    <div class="relative" :style="{ height: `${height}px` }">
      <Bar v-if="type === 'bar'" :data="chartData" :options="barOptions" />
      <Line v-else-if="type === 'line'" :data="chartData" :options="lineOptions" />
      <Doughnut v-else-if="type === 'doughnut'" :data="chartData" :options="doughnutOptions" />
    </div>
    <div v-if="!hasData" class="absolute inset-0 flex items-center justify-center">
      <p class="text-bb-text-muted text-sm">No data yet</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import { Bar, Line, Doughnut } from 'vue-chartjs'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
)

const props = defineProps({
  title: { type: String, default: 'Chart' },
  type: { type: String, default: 'bar' },
  labels: { type: Array, default: () => [] },
  datasets: { type: Array, default: () => [] },
  height: { type: Number, default: 200 },
})

const hasData = computed(() => {
  return props.datasets.some(ds => ds.data && ds.data.length > 0)
})

const chartData = computed(() => ({
  labels: props.labels,
  datasets: props.datasets.map(ds => ({
    ...ds,
    backgroundColor: ds.backgroundColor || 'rgba(0, 230, 118, 0.6)',
    borderColor: ds.borderColor || '#00E676',
    borderWidth: ds.borderWidth ?? 2,
    borderRadius: ds.borderRadius ?? 6,
    tension: ds.tension ?? 0.4,
    fill: ds.fill ?? false,
    pointRadius: ds.pointRadius ?? 3,
    pointBackgroundColor: ds.pointBackgroundColor || '#00E676',
    pointBorderColor: ds.pointBorderColor || '#00E676',
  })),
}))

const sharedOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false,
    },
    tooltip: {
      backgroundColor: '#1A1A1A',
      titleColor: '#FFFFFF',
      bodyColor: '#9E9E9E',
      borderColor: '#333333',
      borderWidth: 1,
      padding: 10,
      cornerRadius: 8,
      displayColors: false,
    },
  },
}

const barOptions = {
  ...sharedOptions,
  indexAxis: 'y',
  scales: {
    x: {
      grid: { color: 'rgba(51, 51, 51, 0.5)', drawBorder: false },
      ticks: { color: '#616161', font: { size: 11 } },
    },
    y: {
      grid: { display: false },
      ticks: { color: '#9E9E9E', font: { size: 11 } },
    },
  },
}

const lineOptions = {
  ...sharedOptions,
  scales: {
    x: {
      grid: { color: 'rgba(51, 51, 51, 0.3)', drawBorder: false },
      ticks: { color: '#616161', font: { size: 10 }, maxTicksLimit: 7 },
    },
    y: {
      grid: { color: 'rgba(51, 51, 51, 0.3)', drawBorder: false },
      ticks: { color: '#616161', font: { size: 10 } },
    },
  },
}

const doughnutOptions = {
  ...sharedOptions,
  cutout: '70%',
  plugins: {
    ...sharedOptions.plugins,
  },
}
</script>

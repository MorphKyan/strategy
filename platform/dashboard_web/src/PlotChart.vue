<script setup lang="ts">
import type { Config, Data, Layout } from 'plotly.js'
import { onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps<{ title: string; data: Data[]; layout?: Partial<Layout> }>()
const host = ref<HTMLElement>()
const error = ref(false)
let plotly: typeof import('plotly.js') | undefined
const config: Partial<Config> = {
  responsive: true,
  displayModeBar: 'hover',
  displaylogo: false,
  modeBarButtonsToRemove: ['select2d', 'lasso2d', 'sendChartToCloud'],
}

watch(host, (element, _, onCleanup) => {
  if (!element) return
  const observer = new ResizeObserver(() => {
    if (plotly && element.clientWidth && element.classList.contains('js-plotly-plot')) void plotly.Plots.resize(element)
  })
  observer.observe(element)
  onCleanup(() => observer.disconnect())
})

watch([host, () => props.data, () => props.layout], async ([element, traces, options], _, onCleanup) => {
  if (!element) return
  let active = true
  onCleanup(() => { active = false })
  try {
    plotly ??= (await import('plotly.js-dist-min')).default
    if (!active) return
    error.value = false
    const axis = { automargin: true, gridcolor: '#ededed', zerolinecolor: '#dfdfdf' }
    await plotly.react(element, traces, {
      autosize: true,
      margin: { l: 48, r: 18, t: 16, b: 40 },
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      font: { color: '#5d5d5d', size: 11 },
      colorway: ['#212121', '#365c78', '#856b38', '#6e5484'],
      ...options,
      xaxis: { ...axis, ...options?.xaxis },
      yaxis: { ...axis, ...options?.yaxis },
    }, config)
  } catch {
    if (active) error.value = true
  }
}, { flush: 'post' })

onBeforeUnmount(() => {
  if (host.value && plotly) plotly.purge(host.value)
})
</script>

<template>
  <div class="plot-frame">
    <div v-show="!error" ref="host" class="plot-chart" role="group" :aria-label="title" />
    <p v-if="error" class="notice" role="alert">图表加载失败，请刷新重试。</p>
  </div>
</template>

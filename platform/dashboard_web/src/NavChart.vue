<script setup lang="ts">
import type { Data, Layout } from 'plotly.js'
import { computed } from 'vue'
import type { NavPoint } from './api'
import PlotChart from './PlotChart.vue'

const props = defineProps<{ points: NavPoint[]; mode: 'nav' | 'drawdown' }>()
const drawdown = computed(() => props.mode === 'drawdown')
const data = computed<Data[]>(() => [{
  type: 'scatter',
  x: props.points.map(point => point.date),
  y: props.points.map(point => drawdown.value ? point.drawdown : point.value),
  mode: props.points.length === 1 ? 'markers' : 'lines',
  line: { color: drawdown.value ? '#5d5d5d' : '#212121', width: 2.4 },
  fill: drawdown.value ? 'tozeroy' : 'none',
  fillcolor: 'rgba(33, 33, 33, .12)',
  hovertemplate: drawdown.value ? '%{x|%Y-%m-%d}<br>%{y:.2%}<extra></extra>' : '%{x|%Y-%m-%d}<br>%{y:,.4~f}<extra></extra>',
}])
const layout = computed<Partial<Layout>>(() => ({
  height: 330,
  hovermode: 'x',
  uirevision: [props.mode, props.points[0]?.date, props.points.at(-1)?.date].join(':'),
  xaxis: { type: 'date', nticks: 6, tickformat: '%m-%d\n%Y' },
  yaxis: { tickformat: drawdown.value ? '.1%' : ',.4~f' },
}))
</script>

<template>
  <PlotChart class="nav-chart" :title="drawdown ? '组合回撤曲线' : '组合净值曲线'" :data="data" :layout="layout" />
</template>

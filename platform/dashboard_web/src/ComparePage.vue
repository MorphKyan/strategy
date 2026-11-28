<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { endpoint, metricText, metrics, useResource, useTemporary, type Figure, type MetricValues, type Mode, type Run } from './api'
import AnalysisPanels from './AnalysisPanels.vue'
import ChoicePicker from './ChoicePicker.vue'
import DataTable from './DataTable.vue'
import PerformanceControls from './PerformanceControls.vue'
import StatusMessage from './StatusMessage.vue'

type Comparison = {
  series: Record<'performance' | 'yearly' | 'risk', Figure[]>
  metrics: (MetricValues & { id: string })[]
  missingScenarios: string[]
  window: [string, string] | null
}
const route = useRoute()
const temporary = useTemporary()
const selected = ref<string[]>([])
const period = ref('全部')
const mode = ref<Mode>('nav')
const overlap = ref(true)
const section = ref<'performance' | 'yearly' | 'risk' | 'scenarios'>('performance')
const scenarioMetric = ref('annualized_return')
const runList = useResource<Run[]>(() => endpoint('/api/runs', { include_temporary: temporary.value }))
const ids = computed(() => (runList.data.value ?? []).map(item => item.id))
let initialized = false
watch(ids, available => {
  if (!runList.data.value) return
  const initial = Array.isArray(route.query.id) ? route.query.id : [route.query.id]
  const applicable = (initialized ? selected.value : initial).filter((id): id is string => id != null && available.includes(id))
  selected.value = initialized || applicable.length >= 2 ? applicable.slice(0, 8) : available.slice(0, 2)
  initialized = true
})
const comparison = useResource<Comparison>(() => selected.value.length >= 2 && ids.value.length
  ? endpoint('/api/compare', { id: selected.value, period: period.value, mode: mode.value, overlap: overlap.value, include_temporary: temporary.value }) : undefined)
const metricRows = computed(() => metrics.map(([key, label, format]) => ({
  指标: label,
  ...Object.fromEntries((comparison.data.value?.metrics ?? []).map(run => [run.id, metricText(run[key], format)])),
})))
const scenarioKeys = ['annualized_return', 'sharpe_ratio', 'max_drawdown', 'annualized_turnover', 'trade_count', 'rejected_order_count']
const scenarioRows = computed(() => (comparison.data.value?.metrics ?? []).map(run => ({
  回测: run.id, 滑点场景: run.slippage_scenario,
  ...Object.fromEntries(metrics.filter(([key]) => scenarioKeys.includes(key)).map(([key, label, format]) => [label, metricText(run[key], format)])),
})))
const scenarioOptions = metrics.filter(([key]) => scenarioKeys.slice(0, 4).includes(key))
const scenarioCharts = computed<Figure[]>(() => {
  const { metrics: values } = comparison.data.value ?? { metrics: [] }
  const metric = scenarioOptions.find(([key]) => key === scenarioMetric.value)
  const valid = values.filter(run => ['default', 'stress', 'dynamic_participation'].includes(String(run.slippage_scenario)))
  return metric && valid.length ? [{
    title: metric[1],
    data: valid.map(run => ({ type: 'bar', x: [run.slippage_scenario], y: [run[metric[0]]], name: run.id })),
    layout: { height: 320, barmode: 'group', yaxis: { tickformat: metric[2] === 'percent' ? '.1%' : undefined }, legend: { orientation: 'h' } },
  }] : []
})
</script>

<template>
  <div class="page-stack">
    <header class="page-heading"><h1>回测对比</h1></header>
    <StatusMessage :loading="runList.loading.value" :error="runList.error.value" />
    <ChoicePicker v-if="ids.length" v-model="selected" :choices="ids" :max="8" title="选择 2–8 个回测" />
    <div v-if="runList.data.value && selected.length < 2" class="panel empty-state"><p>请选择至少两个可用的回测。</p></div>
    <template v-if="selected.length >= 2">
      <PerformanceControls v-model:period="period" v-model:mode="mode">
        <label class="check-field"><input v-model="overlap" type="checkbox">仅对比共同重叠区间</label>
      </PerformanceControls>
      <StatusMessage :loading="comparison.loading.value" :error="comparison.error.value" />
      <template v-if="comparison.data.value">
        <div class="view-tabs" role="group" aria-label="对比视图">
          <button type="button" :aria-pressed="section === 'performance'" @click="section = 'performance'">净值与指标</button>
          <button type="button" :aria-pressed="section === 'yearly'" @click="section = 'yearly'">年度收益</button>
          <button type="button" :aria-pressed="section === 'risk'" @click="section = 'risk'">滚动风险</button>
          <button type="button" :aria-pressed="section === 'scenarios'" @click="section = 'scenarios'">三滑点场景</button>
        </div>
        <template v-if="section === 'scenarios'">
          <p v-if="comparison.data.value.missingScenarios.length" class="notice" role="status">所选回测缺少场景 {{ comparison.data.value.missingScenarios.join('、') }}。</p>
          <label class="field inline-field control-select"><span>场景指标</span><select v-model="scenarioMetric"><option v-for="[key, label] in scenarioOptions" :key="key" :value="key">{{ label }}</option></select></label>
          <AnalysisPanels :charts="scenarioCharts" />
          <DataTable title="滑点场景明细" :rows="scenarioRows" />
        </template>
        <template v-else>
          <p v-if="section === 'performance' && comparison.data.value.window" class="context-line">
            {{ comparison.data.value.window.join(' 至 ') }} · 区间首日归一
          </p>
          <AnalysisPanels :charts="comparison.data.value.series[section]" empty="所选区间暂无足够的可比数据" />
          <DataTable v-if="section === 'performance'" title="指标对照 · 全样本" :rows="metricRows" />
        </template>
      </template>
    </template>
  </div>
</template>

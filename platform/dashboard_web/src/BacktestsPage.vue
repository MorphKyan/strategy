<script setup lang="ts">
import { Search } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { endpoint, metricText, metrics, performanceClass, useResource, useTemporary, type Analysis, type MetricValues, type Mode, type Run } from './api'
import AnalysisPanels from './AnalysisPanels.vue'
import Button from './Button.vue'
import DataTable from './DataTable.vue'
import PerformanceControls from './PerformanceControls.vue'
import StatusMessage from './StatusMessage.vue'

const route = useRoute()
const router = useRouter()
const temporary = useTemporary()
const draft = ref('')
const query = ref('')
const period = ref('全部')
const mode = ref<Mode>('nav')
const logarithmic = ref(false)
const benchmark = ref('')
const asset = ref('')
const sections = [
  ['performance', '净值与回撤'], ['returns', '收益分解'], ['positions', '持仓'],
  ['rebalance', '调仓与行情'], ['execution', '订单与交易'], ['info', '运行信息'],
] as const
const section = ref<typeof sections[number][0]>('performance')

type Detail = Run & { metrics: MetricValues; split: { training: MetricValues; oos: MetricValues } | null; manifest: string; config: string | null }
const runs = useResource<Run[]>(() => endpoint('/api/runs', { include_temporary: temporary.value }))
const matches = useResource<Run[]>(() => query.value ? endpoint('/api/runs', { query: query.value, include_temporary: temporary.value }) : undefined)
const choices = computed(() => query.value ? matches.data.value : runs.data.value)
const current = computed(() => choices.value?.find(item => item.id === route.query.id) ?? choices.value?.[0])
const detail = useResource<Detail>(() => current.value && endpoint('/api/run', { id: current.value.id, include_temporary: temporary.value }))
const benchmarkOptions = computed(() => (runs.data.value ?? []).filter(item => item.id !== current.value?.id)
  .map(item => ({ value: item.id, label: item.id })))
const analysis = useResource<Analysis>(() => {
  if (!current.value || section.value === 'info') return
  return endpoint('/api/run/analysis', {
    id: current.value.id, section: section.value, include_temporary: temporary.value,
    period: section.value === 'performance' ? period.value : undefined,
    mode: section.value === 'performance' ? mode.value : undefined,
    benchmark_id: section.value === 'performance' && benchmarkOptions.value.some(option => option.value === benchmark.value) ? benchmark.value : undefined,
    log: section.value === 'performance' ? logarithmic.value : undefined,
    asset: section.value === 'rebalance' && asset.value ? asset.value : undefined,
  })
})
const layoutMetrics = computed(() => metrics.filter(([key]) => !['execution_slippage', 'slippage_scenario'].includes(key)))
const splitRows = computed(() => {
  const split = detail.data.value?.split
  return split ? metrics.slice(1, 5).map(([key, label, format]) => ({
    指标: label, 训练样本: metricText(split.training[key], format), 冻结样本: metricText(split.oos[key], format),
  })) : []
})
watch(() => current.value?.id, () => { asset.value = ''; benchmark.value = '' })
function choose(id: string) {
  void router.replace({ name: 'backtests', query: id ? { id } : {} })
}
function search(value: string) {
  draft.value = value
  query.value = value.trim()
  choose('')
}
</script>

<template>
  <div class="page-stack">
    <header class="page-heading"><h1>回测分析</h1></header>
    <div class="filter-bar">
      <form class="search-form" role="search" @submit.prevent="search(draft)">
        <label class="field grow-field"><span>搜索回测</span><span class="search-field"><Search :size="16" aria-hidden="true" /><input v-model="draft" type="search" placeholder="运行名、策略、日期或滑点场景"></span></label>
        <Button type="submit">搜索</Button><Button v-if="query" variant="ghost" @click="search('')">清除</Button>
      </form>
      <label v-if="choices?.length" class="field grow-field"><span>选择回测</span>
        <select :value="current?.id" aria-label="选择回测" @change="choose(($event.target as HTMLSelectElement).value)">
          <option v-for="item in choices" :key="item.id" :value="item.id">{{ item.id }}</option>
        </select>
      </label>
    </div>
    <StatusMessage :loading="runs.loading.value || matches.loading.value || detail.loading.value" :error="runs.error.value || matches.error.value || detail.error.value" />
    <div v-if="choices && !choices.length" class="panel empty-state"><p>{{ query ? '没有匹配的回测' : '暂无可读取的回测结果' }}</p></div>
    <template v-if="detail.data.value">
      <p class="context-line"><strong>{{ detail.data.value.id }}</strong><span>{{ detail.data.value.start || '—' }} 至 {{ detail.data.value.end || '—' }}</span><span class="kind">{{ detail.data.value.metrics.slippage_scenario }}</span></p>
      <div class="metrics-grid metrics-dense" aria-label="回测指标">
        <section v-for="[key, label, format] in layoutMetrics" :key="key" class="metric metric-text">
          <p class="metric-label">{{ label }}</p>
          <p class="metric-value" :class="['total_return', 'annualized_return', 'max_drawdown'].includes(key) ? performanceClass(detail.data.value.metrics[key] as number) : undefined">{{ metricText(detail.data.value.metrics[key], format) }}</p>
        </section>
      </div>
      <details v-if="splitRows.length" class="panel disclosure"><summary>训练样本与冻结测试样本</summary><DataTable title="样本指标" :rows="splitRows" /></details>
      <div class="view-tabs" role="group" aria-label="分析视图">
        <button v-for="[key, label] in sections" :key="key" type="button" :aria-pressed="section === key" @click="section = key">{{ label }}</button>
      </div>
      <PerformanceControls v-if="section === 'performance'" v-model:period="period" v-model:mode="mode"
        v-model:benchmark="benchmark" v-model:logarithmic="logarithmic" :benchmark-options="benchmarkOptions" show-log />
      <label v-if="section === 'rebalance' && (analysis.data.value?.assets?.length || asset)" class="field inline-field control-select">
        <span>叠加行情合约</span><select :value="asset || analysis.data.value?.asset" @change="asset = ($event.target as HTMLSelectElement).value">
          <option v-for="item in analysis.data.value?.assets ?? (asset ? [asset] : [])" :key="item">{{ item }}</option>
        </select>
      </label>
      <template v-if="section === 'info'">
        <details class="panel disclosure" open><summary>运行清单</summary><pre>{{ detail.data.value.manifest }}</pre></details>
        <details v-if="detail.data.value.config" class="panel disclosure"><summary>配置快照</summary><pre>{{ detail.data.value.config }}</pre></details>
      </template>
      <template v-else>
        <StatusMessage :loading="analysis.loading.value" :error="analysis.error.value" />
        <AnalysisPanels v-if="analysis.data.value" :charts="analysis.data.value.charts" :tables="analysis.data.value.tables"
          :note="analysis.data.value.note" empty="当前回测暂无可展示数据" />
      </template>
    </template>
  </div>
</template>

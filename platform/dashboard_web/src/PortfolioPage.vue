<script setup lang="ts">
import { BriefcaseBusiness, CalendarDays, ChevronDown, Coins, TrendingDown, TrendingUp, Wallet } from '@lucide/vue'
import { computed, inject, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { endpoint, formatNumber, formatPercent, formatQuantity, get, kindLabel, metricText, performanceClass, portfolioQuery, useResource, useTemporary, type Analysis, type Mode, type NamedTable, type Period, type Portfolio, type PortfolioDetail, type Run } from './api'
import NavChart from './NavChart.vue'
import AnalysisPanels from './AnalysisPanels.vue'
import DataTable from './DataTable.vue'
import PerformanceControls from './PerformanceControls.vue'
import StatusMessage from './StatusMessage.vue'

const route = useRoute()
const router = useRouter()
const revision = inject('refresh', ref(0))
type Choice = Pick<Portfolio, 'kind' | 'id'>
const choices = ref<Choice[]>([])
const data = ref<PortfolioDetail>()
const error = ref('')
const listError = ref('')
const loadingChoices = ref(true)
const loadingDetail = ref(false)
const period = ref<Period>('全部')
const periods: Period[] = ['全部', '近1月', '近3月', '近1年']
const mode = ref<'nav' | 'drawdown'>('nav')
const section = ref<'snapshot' | 'performance' | 'returns' | 'activity'>('snapshot')
const analysisPeriod = ref('全部')
const analysisMode = ref<Mode>('nav')
const logarithmic = ref(false)
const benchmark = ref('')
const temporary = useTemporary()

const runs = useResource<Run[]>(() => section.value === 'performance'
  ? endpoint('/api/runs', { include_temporary: temporary.value }) : undefined)

watch(revision, async (_, __, onCleanup) => {
  const request = new AbortController()
  onCleanup(() => request.abort())
  listError.value = ''
  loadingChoices.value = true
  try {
    choices.value = await get<Choice[]>('/api/portfolios', request.signal)
  } catch (failure) {
    if (!request.signal.aborted) listError.value = failure instanceof Error ? failure.message : '组合列表读取失败。'
  } finally {
    if (!request.signal.aborted) loadingChoices.value = false
  }
}, { immediate: true })

const choiceKey = (item: Choice) => `${item.kind}:${item.id}`
const selection = computed<Choice | undefined>(() => {
  const { kind, id } = route.query
  if ((kind === 'live' || kind === 'sim') && typeof id === 'string') return { kind, id }
  return choices.value[0]
})

watch([() => selection.value?.kind, () => selection.value?.id, revision], async ([kind, id], previous, onCleanup) => {
  const request = new AbortController()
  onCleanup(() => request.abort())
  error.value = ''
  if (!previous || kind !== previous[0] || id !== previous[1]) {
    period.value = '全部'
    benchmark.value = ''
    data.value = undefined
  }
  if (!kind || !id) {
    loadingDetail.value = false
    return
  }
  loadingDetail.value = true
  try {
    data.value = await get<PortfolioDetail>(`/api/portfolio?${new URLSearchParams({ kind, id })}`, request.signal)
  } catch (failure) {
    if (!request.signal.aborted) error.value = failure instanceof Error ? failure.message : '组合详情读取失败。'
  } finally {
    if (!request.signal.aborted) loadingDetail.value = false
  }
}, { immediate: true })

function choose(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  const selected = choices.value.find(item => choiceKey(item) === value)
  if (selected) void router.push({ name: 'portfolio', query: portfolioQuery(selected) })
}

const metrics = computed(() => {
  const item = data.value
  if (!item) return []
  return [
    { label: '最新总值', value: formatNumber(item.totalValue), tone: '', icon: Wallet },
    { label: '现金', value: formatNumber(item.cash), tone: '', icon: Coins },
    { label: '成立以来', value: formatPercent(item.returnSinceStart), tone: performanceClass(item.returnSinceStart), icon: TrendingUp },
    { label: '最大回撤', value: formatPercent(item.maxDrawdown), tone: performanceClass(item.maxDrawdown), icon: TrendingDown },
  ]
})

const points = computed(() => {
  const first = data.value?.windows[period.value]
  return data.value?.series.filter(point => !first || point.date >= first) ?? []
})

const benchmarkOptions = computed(() => [
  ...choices.value.filter(item => choiceKey(item) !== (selection.value && choiceKey(selection.value))).map(item => ({
    value: JSON.stringify(item), label: kindLabel(item.kind) + ' · ' + item.id, kind: item.kind, id: item.id,
  })),
  ...(runs.data.value ?? []).map(item => ({ value: JSON.stringify(['run', item.id]), label: '回测 · ' + item.id, kind: 'run' as const, id: item.id })),
])
const analysis = useResource<Analysis>(() => {
  if (!selection.value || (section.value !== 'performance' && section.value !== 'returns')) return
  const baseline = section.value === 'performance' ? benchmarkOptions.value.find(item => item.value === benchmark.value) : undefined
  return endpoint('/api/portfolio/analysis', {
    ...selection.value, section: section.value, period: analysisPeriod.value, mode: analysisMode.value, log: logarithmic.value,
    benchmark_run: baseline?.kind === 'run' ? baseline.id : undefined,
    benchmark_kind: baseline?.kind === 'run' ? undefined : baseline?.kind,
    benchmark_id: baseline?.kind === 'run' ? undefined : baseline?.id,
    include_temporary: temporary.value,
  })
})
const activity = useResource<NamedTable[]>(() => selection.value && section.value === 'activity'
  ? endpoint('/api/portfolio/activity', selection.value) : undefined)
const summaryMetrics = [
  ['annualized_return', '年化收益', 'percent'], ['annualized_volatility', '年化波动', 'percent'],
  ['sharpe_ratio', 'Sharpe', 'decimal'], ['current_drawdown', '当前回撤', 'percent'],
] as const
</script>

<template>
  <div class="page-stack" :aria-busy="loadingChoices || loadingDetail">
    <header class="detail-heading">
      <div class="detail-title">
        <div class="title-line"><h1>组合详情</h1><span v-if="data" class="kind" :class="data.kind">{{ kindLabel(data.kind) }}</span></div>
        <p v-if="data" class="date-line"><CalendarDays :size="15" aria-hidden="true" /> <span>净值日期 {{ data.asOf ?? '—' }}</span><span v-if="(data.businessDaysBehind ?? 0) >= 3" class="date-lag">滞后 {{ data.businessDaysBehind }} 个工作日</span></p>
      </div>
      <label v-if="choices.length" class="portfolio-select">
        <span class="sr-only">选择组合</span>
        <select :value="selection && choiceKey(selection)" @change="choose">
          <option v-for="item in choices" :key="choiceKey(item)" :value="choiceKey(item)">{{ kindLabel(item.kind) }} · {{ item.id }}</option>
        </select>
        <ChevronDown :size="16" aria-hidden="true" />
      </label>
    </header>

    <p v-if="error || listError" class="notice" role="alert">{{ error || listError }}</p>
    <template v-if="data">
      <p v-if="data.qualityNote" class="notice">{{ data.qualityNote }}</p>
      <div class="metrics-grid" aria-label="组合指标">
        <section v-for="metric in metrics" :key="metric.label" class="metric">
          <span class="metric-icon"><component :is="metric.icon" :size="17" :stroke-width="1.8" aria-hidden="true" /></span>
          <div><p class="metric-label">{{ metric.label }}</p><p class="metric-value" :class="metric.tone">{{ metric.value }}</p></div>
        </section>
      </div>

      <div class="view-tabs" role="group" aria-label="组合视图">
        <button type="button" :aria-pressed="section === 'snapshot'" @click="section = 'snapshot'">当前概况</button>
        <button type="button" :aria-pressed="section === 'performance'" @click="section = 'performance'">净值与基准</button>
        <button type="button" :aria-pressed="section === 'returns'" @click="section = 'returns'">收益分解</button>
        <button type="button" :aria-pressed="section === 'activity'" @click="section = 'activity'">{{ data.kind === 'live' ? '实盘成交' : '票据与交易' }}</button>
      </div>
      <template v-if="section === 'snapshot'">
      <div class="detail-grid">
        <section class="panel chart-panel">
          <header class="panel-heading chart-heading">
            <h2>{{ mode === 'nav' ? '净值走势' : '回撤走势' }}</h2>
            <div class="segments" role="group" aria-label="净值区间">
              <button v-for="item in periods" :key="item" type="button" :aria-pressed="period === item" @click="period = item">{{ item }}</button>
            </div>
          </header>
          <div class="chart-controls">
            <div class="segments" role="group" aria-label="图表指标">
              <button type="button" :aria-pressed="mode === 'nav'" @click="mode = 'nav'">净值</button>
              <button type="button" :aria-pressed="mode === 'drawdown'" @click="mode = 'drawdown'">回撤</button>
            </div>
            <span v-if="points.length" class="chart-dates">{{ points[0]?.date }} 至 {{ points.at(-1)?.date }}</span>
          </div>
          <NavChart v-if="points.length" :points="points" :mode="mode" />
          <div v-else class="empty-state chart-empty"><p>该区间暂无净值数据</p></div>
        </section>

        <div class="page-stack">
        <section class="panel positions-panel">
          <header class="panel-heading"><h2>当前持仓</h2></header>
          <div v-if="data.positions.length" class="table-scroll">
            <table class="data-table positions-table">
              <thead><tr><th scope="col">资产</th><th scope="col" class="numeric">数量</th><th scope="col" class="numeric">市值</th><th scope="col" class="numeric">权重</th></tr></thead>
              <tbody>
                <tr v-for="item in data.positions" :key="item.id">
                  <td><strong :title="item.id">{{ item.code }}</strong><span v-if="item.priceDate" class="price-date">{{ item.priceDate }}</span><span v-else-if="item.quantity !== null" class="price-date">缺少报价</span></td>
                  <td class="numeric">{{ formatQuantity(item.quantity) }}</td>
                  <td class="numeric">{{ formatNumber(item.marketValue) }}</td>
                  <td class="numeric">{{ formatPercent(item.weight) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="empty-state"><p>暂无持仓</p></div>
        </section>
        <AnalysisPanels :charts="data.weights" />
        </div>
      </div>
      <div class="summary-strip" aria-label="扩展组合指标">
        <div v-for="[key, label, format] in summaryMetrics" :key="key"><span>{{ label }}</span><strong>{{ metricText(data.metrics[key], format) }}</strong></div>
        <div><span>待执行意图</span><strong>{{ formatNumber(data.pendingCount) }}</strong></div>
      </div>
      <p v-if="data.metrics.observations > 0 && data.metrics.observations < 20" class="context-line">净值样本共 {{ data.metrics.observations }} 天，年化指标需要至少 20 天。</p>
      <DataTable v-if="data.pending.length" title="待执行意图" :rows="data.pending" />
      <details v-if="data.ticket" class="panel disclosure">
        <summary>最新下单票 · {{ data.ticket.date }}</summary><pre>{{ data.ticket.text }}</pre>
        <DataTable v-if="data.ticket.orders.length" title="票据订单" :rows="data.ticket.orders" />
      </details>
      </template>
      <template v-else-if="section === 'activity'">
        <StatusMessage :loading="activity.loading.value" :error="activity.error.value" />
        <AnalysisPanels v-if="activity.data.value" :tables="activity.data.value" />
      </template>
      <template v-else>
        <PerformanceControls v-if="section === 'performance'" v-model:period="analysisPeriod" v-model:mode="analysisMode"
          v-model:benchmark="benchmark" v-model:logarithmic="logarithmic" :benchmark-options="benchmarkOptions" show-log />
        <StatusMessage :loading="analysis.loading.value" :error="analysis.error.value || (section === 'performance' ? runs.error.value : '')" />
        <AnalysisPanels v-if="analysis.data.value" v-bind="analysis.data.value" empty="暂无足够的净值数据" />
      </template>
    </template>
    <p v-else-if="loadingChoices || loadingDetail" class="loading-state" role="status">正在读取组合…</p>
    <div v-else-if="!error && !listError" class="panel empty-state"><BriefcaseBusiness :size="22" /><p>暂无实盘或模拟组合</p></div>
  </div>
</template>

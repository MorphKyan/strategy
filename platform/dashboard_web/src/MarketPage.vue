<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Data, Layout } from 'plotly.js'
import { endpoint, formatPercent, useResource, type Analysis, type Row } from './api'
import AnalysisPanels from './AnalysisPanels.vue'
import ChoicePicker from './ChoicePicker.vue'
import DataTable from './DataTable.vue'
import PlotChart from './PlotChart.vue'
import StatusMessage from './StatusMessage.vue'

type Price = { trade_date: string; open?: number | null; high?: number | null; low?: number | null; close: number }
type History = { prices: Price[]; dividends: Row[]; splits: Row[] }
const marketMode = ref<'single' | 'basket'>('single')
const chartStyle = ref<'candles' | 'close'>('candles')
const symbols = useResource<string[]>(() => '/api/market/symbols')
const selected = ref('')
const symbol = computed(() => selected.value || symbols.data.value?.[0])
const history = useResource<History>(() => marketMode.value === 'single' && symbol.value
  ? endpoint('/api/market/history', { symbol: symbol.value }) : undefined)
const start = ref('')
const end = ref('')
const bounds = computed(() => [history.data.value?.prices[0]?.trade_date.slice(0, 10) ?? '', history.data.value?.prices.at(-1)?.trade_date.slice(0, 10) ?? ''])
watch(symbol, () => { start.value = ''; end.value = '' })
const datesValid = computed(() => !start.value || !end.value || start.value <= end.value)
const prices = computed(() => (history.data.value?.prices ?? []).filter(item => {
  const day = item.trade_date.slice(0, 10)
  return (!start.value || day >= start.value) && (!end.value || day <= end.value)
}))
const traces = computed<Data[]>(() => {
  const records = prices.value
  if (!records.length) return []
  const x = records.map(item => item.trade_date)
  const candles = records.filter((item): item is Price & { open: number; high: number; low: number } =>
    item.open != null && item.high != null && item.low != null)
  const figures: Data[] = chartStyle.value === 'candles' && candles.length ? [{
    type: 'candlestick', name: symbol.value, x: candles.map(item => item.trade_date), close: candles.map(item => item.close),
    open: candles.map(item => item.open), high: candles.map(item => item.high), low: candles.map(item => item.low),
    increasing: { line: { color: '#c62828' } }, decreasing: { line: { color: '#167147' } },
  }] : [{ type: 'scatter', mode: 'lines', name: symbol.value, x, y: records.map(item => item.close) }]
  for (const [key, day, field, label, color] of [
    ['dividends', 'ex_date', 'dividend_per_share', '分红', '#856b38'],
    ['splits', 'split_date', 'split_ratio', '转送 / 折算', '#6e5484'],
  ] as const) {
    const actions = (history.data.value?.[key] ?? []).filter(item => {
      const date = String(item[day] ?? '').slice(0, 10)
      return date && date >= String(x[0]).slice(0, 10) && date <= String(x.at(-1)).slice(0, 10) && item.close != null
    })
    if (actions.length) figures.push({
      type: 'scatter', mode: 'markers', name: label, x: actions.map(item => String(item[day])),
      y: actions.map(item => Number(item.close)), text: actions.map(item => String(item[field] ?? '')),
      marker: { size: 9, color, symbol: 'diamond' }, hovertemplate: '%{x|%Y-%m-%d}<br>%{text}<extra>%{fullData.name}</extra>',
    })
  }
  return figures
})
const layout = computed<Partial<Layout>>(() => ({
  height: 420, xaxis: { type: 'date', rangeslider: { visible: true, thickness: 0.06 } },
  uirevision: [symbol.value, start.value, end.value].join(':'),
  legend: { orientation: 'h' }, showlegend: traces.value.length > 1,
}))

const basketSymbols = ref<string[]>([])
const inputWeights = ref<Record<string, number>>({})
const riskWindow = ref(252)
const applied = ref<{ symbol: string[]; weight: string[]; window: number }>()
function calculate() {
  if (!basketSymbols.value.length) return
  applied.value = {
    symbol: [...basketSymbols.value],
    weight: basketSymbols.value.map(item => String(inputWeights.value[item] || 0)),
    window: riskWindow.value,
  }
}
watch(basketSymbols, list => {
  for (const item of list) {
    if (inputWeights.value[item] === undefined) inputWeights.value[item] = 1 / list.length
  }
  if (!list.length) applied.value = undefined
})
watch(symbols.data, list => {
  if (!list || applied.value) return
  basketSymbols.value = list.slice(0, 3)
  inputWeights.value = Object.fromEntries(basketSymbols.value.map(item => [item, 1 / basketSymbols.value.length]))
  calculate()
}, { once: true })
const basket = useResource<Analysis & { contribution: Row[] }>(() => marketMode.value === 'basket' && applied.value
  ? endpoint('/api/market/basket', applied.value) : undefined)
const contribution = computed(() => (basket.data.value?.contribution ?? []).map(item => ({
  合约: item.symbol, 权重: formatPercent(item.weight as number | null),
  年化波动贡献: formatPercent(item.risk_contribution as number | null),
  贡献占比: formatPercent(item.risk_contribution_pct as number | null),
})))
</script>

<template>
  <div class="page-stack">
    <header class="page-heading"><h1>市场数据</h1></header>
    <StatusMessage :loading="symbols.loading.value" :error="symbols.error.value" />
    <div v-if="symbols.data.value?.length === 0" class="panel empty-state"><p>暂无本地行情数据</p></div>
    <template v-if="symbols.data.value?.length">
      <div class="view-tabs" role="group" aria-label="行情视图">
        <button type="button" :aria-pressed="marketMode === 'single'" @click="marketMode = 'single'">单合约</button>
        <button type="button" :aria-pressed="marketMode === 'basket'" @click="marketMode = 'basket'">多合约组合</button>
      </div>
      <template v-if="marketMode === 'single'">
        <div class="filter-bar">
          <label class="field"><span>合约</span><select :value="symbol" @change="selected = ($event.target as HTMLSelectElement).value"><option v-for="item in symbols.data.value" :key="item">{{ item }}</option></select></label>
          <label class="field"><span>开始日期</span><input type="date" :min="bounds[0]" :max="bounds[1]" :value="start || bounds[0]" @change="start = ($event.target as HTMLInputElement).value"></label>
          <label class="field"><span>结束日期</span><input type="date" :min="bounds[0]" :max="bounds[1]" :value="end || bounds[1]" @change="end = ($event.target as HTMLInputElement).value"></label>
          <label class="field"><span>图表</span><select v-model="chartStyle" aria-label="图表"><option value="candles">K 线</option><option value="close">收盘价</option></select></label>
        </div>
        <StatusMessage :loading="history.loading.value" :error="history.error.value" />
        <p v-if="!datesValid" class="notice" role="alert">开始日期需早于或等于结束日期。</p>
        <template v-if="history.data.value">
          <section v-if="traces.length" class="panel">
            <header class="panel-heading"><h2>{{ symbol }} 行情</h2></header>
            <PlotChart :title="String(symbol) + ' 行情'" :data="traces" :layout="layout" />
          </section>
          <div v-else-if="datesValid" class="panel empty-state"><p>所选日期暂无行情</p></div>
          <div class="equal-grid">
            <DataTable title="历史分红" :rows="history.data.value.dividends.map(({ close, ...item }) => item)" />
            <DataTable title="历史转送与份额折算" :rows="history.data.value.splits.map(({ close, ...item }) => item)" />
          </div>
        </template>
      </template>
      <template v-else>
        <ChoicePicker v-model="basketSymbols" :choices="symbols.data.value" :max="10" title="选择合约" />
        <form v-if="basketSymbols.length" class="filter-bar" @submit.prevent="calculate">
          <label v-for="item in basketSymbols" :key="item" class="field weight-field">
            <span>{{ item }} 权重</span><input v-model.number="inputWeights[item]" type="number" min="0" step="any" required>
          </label>
          <label class="field"><span>风险估计窗口</span><select v-model.number="riskWindow" aria-label="风险估计窗口">
            <option v-for="item in [60, 120, 252, 504, 1000, 0]" :key="item" :value="item">{{ item ? item + ' 日' : '全部' }}</option>
          </select></label>
          <button type="submit" class="primary-button">计算组合</button>
        </form>
        <div v-else class="panel empty-state"><p>请至少选择一个合约。</p></div>
        <StatusMessage :loading="basket.loading.value" :error="basket.error.value" />
        <template v-if="basket.data.value">
          <p class="context-line"><strong>计算合约</strong>{{ applied?.symbol.join('、') }}</p>
          <AnalysisPanels :charts="basket.data.value.charts" :note="basket.data.value.note" />
          <DataTable v-if="contribution.length" title="风险贡献明细" :rows="contribution" />
        </template>
      </template>
    </template>
  </div>
</template>

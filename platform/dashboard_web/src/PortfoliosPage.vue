<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { endpoint, formatNumber, formatPercent, kindLabel, performanceClass, portfolioQuery, useResource, type Portfolio, type Row } from './api'
import DataTable from './DataTable.vue'

const { data, loading, error } = useResource<Portfolio[]>(() => endpoint('/api/portfolios', { summary: true }))
const filter = ref('')
const ranges = ['近1周', '近1月', '近3月', '近6月', '今年']
const columns = [
  { key: 'id', label: '组合' }, { key: 'kindLabel', label: '类型' }, { key: 'asOf', label: '净值日期' },
  { key: 'totalValue', label: '总值', numeric: true, format: (value: unknown) => formatNumber(value as number | null) },
  ...[...ranges, 'returnSinceStart', 'maxDrawdown'].map(key => ({
    key, label: key === 'returnSinceStart' ? '成立以来' : key === 'maxDrawdown' ? '最大回撤' : key, numeric: true,
  })),
  { key: 'pendingCount', label: '待执行意图', numeric: true },
]
const returns = [...ranges, 'returnSinceStart', 'maxDrawdown']
const rows = computed<Row[]>(() => (data.value ?? []).filter(item => !filter.value || item.kind === filter.value).map(item => ({
  ...item, ...item.returns, kindLabel: kindLabel(item.kind),
})))
function toPortfolio(row: Row) {
  return { name: 'portfolio', query: portfolioQuery({ kind: row.kind as Portfolio['kind'], id: String(row.id) }) }
}
</script>

<template>
  <div class="page-stack" :aria-busy="loading">
    <header class="page-heading"><h1>组合总览</h1>
      <label class="field inline-field"><span>类型</span><select v-model="filter" aria-label="类型"><option value="">全部组合</option><option value="live">实盘</option><option value="sim">模拟</option></select></label>
    </header>
    <p v-if="error" class="notice" role="alert">{{ error }}</p>
    <p v-if="loading && !data" class="loading-state" role="status">正在读取组合…</p>
    <DataTable v-if="data" title="组合列表" :rows="rows" :columns="columns" empty="暂无符合条件的组合">
      <template #id="{ row }"><RouterLink class="text-link" :to="toPortfolio(row)">{{ row.id }}</RouterLink></template>
      <template #asOf="{ row }">
        {{ row.asOf ?? '无净值' }}
        <span v-if="Number(row.businessDaysBehind) >= 3" class="date-lag">滞后 {{ row.businessDaysBehind }} 个工作日</span>
      </template>
      <template v-for="key in returns" #[key]="{ value }">
        <span :class="performanceClass(value as number | null)">{{ formatPercent(value as number | null) }}</span>
      </template>
    </DataTable>
  </div>
</template>

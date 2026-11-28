import { computed, inject, ref, shallowRef, watch } from 'vue'
import type { Data, Layout } from 'plotly.js'

export type Period = '全部' | '近1月' | '近3月' | '近1年'
export const periods = ['全部', '近1月', '近3月', '近6月', '今年', '近1年', '近2年', '近3年'] as const
export type Mode = 'nav' | 'return'
export type Row = Record<string, unknown>
export type Figure = { title: string; data: Data[]; layout: Partial<Layout> }
export type NamedTable = { title: string; rows: Row[] }
export type Analysis = { charts?: Figure[]; tables?: NamedTable[]; note?: string; assets?: string[]; asset?: string }
export type Run = { id: string; date: string; start: string; end: string; scenario: string }
export type MetricValues = Record<string, number | string | null>

export interface Portfolio {
  id: string
  kind: 'live' | 'sim'
  asOf: string | null
  businessDaysBehind: number | null
  totalValue: number | null
  returnSinceStart: number | null
  maxDrawdown: number | null
  pendingCount: number
  returns: Record<string, number | null>
}

export interface Overview {
  portfolios: Portfolio[]
  configCount: number
  strategyCount: number
  runCount: number
  strategies: { name: string; count: number }[]
  recentRuns: (Run & { annualizedReturn: number | null; maxDrawdown: number | null })[]
}

export interface NavPoint {
  date: string
  value: number | null
  drawdown: number | null
}

export interface PortfolioDetail extends Portfolio {
  cash: number | null
  qualityNote: string | null
  windows: Partial<Record<Period, string>>
  series: NavPoint[]
  metrics: MetricValues & { observations: number }
  weights: Figure[]
  pending: Row[]
  ticket: { date: string; text: string; orders: Row[] } | null
  positions: {
    id: string
    code: string
    quantity: number | null
    marketValue: number | null
    weight: number | null
    priceDate: string | null
  }[]
}

export function endpoint(path: string, params: Record<string, string | boolean | number | readonly string[] | undefined> = {}) {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
      query.append(key, String(value))
    } else if (value) {
      for (const item of value) query.append(key, item)
    }
  }
  return query.size ? path + '?' + query : path
}

export async function get<T>(path: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal, cache: 'no-store' })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(typeof body?.detail === 'string' ? body.detail : '本地数据读取失败，请刷新重试。')
  }
  return response.json() as Promise<T>
}

export function useResource<T>(path: () => string | undefined) {
  const revision = inject('refresh', ref(0))
  const data = shallowRef<T>()
  const loading = ref(Boolean(path()))
  const error = ref('')
  watch([computed(path), revision], async ([url], previous, onCleanup) => {
    const request = new AbortController()
    onCleanup(() => request.abort())
    if (url !== previous?.[0]) data.value = undefined
    loading.value = Boolean(url)
    error.value = ''
    if (!url) return
    try {
      const value = await get<T>(url, request.signal)
      if (!request.signal.aborted) data.value = value
    } catch (failure) {
      if (!request.signal.aborted) error.value = failure instanceof Error ? failure.message : '读取失败。'
    } finally {
      if (!request.signal.aborted) loading.value = false
    }
  }, { immediate: true })
  return { data, loading, error }
}

export const useTemporary = () => inject('includeTemporary', ref(false))

const integer = new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 0 })
const quantity = new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 4 })
const percent = new Intl.NumberFormat('zh-CN', { style: 'percent', minimumFractionDigits: 2, maximumFractionDigits: 2 })

export const formatNumber = (value: number | null | undefined) => value == null ? '—' : integer.format(value)
export const formatQuantity = (value: number | null | undefined) => value == null ? '—' : quantity.format(value)
export const formatPercent = (value: number | null | undefined) => value == null ? '—' : percent.format(value)
export const performanceClass = (value: number | null | undefined) => value == null || value === 0 ? '' : value > 0 ? 'gain' : 'loss'
export const kindLabel = (kind: Portfolio['kind']) => kind === 'live' ? '实盘' : '模拟'
export const portfolioQuery = ({ kind, id }: Pick<Portfolio, 'kind' | 'id'>) => ({ kind, id })

export const metrics = [
  ['total_return', '累计收益', 'percent'], ['annualized_return', '年化收益', 'percent'],
  ['annualized_volatility', '年化波动', 'percent'], ['max_drawdown', '最大回撤', 'percent'],
  ['sharpe_ratio', 'Sharpe', 'decimal'], ['annualized_turnover', '年化换手', 'percent'],
  ['annualized_fee_drag', '年化费用拖累', 'percent'], ['execution_slippage', '执行滑点', 'percent'],
  ['trade_count', '交易数', 'integer'], ['order_count', '订单数', 'integer'],
  ['rejected_order_count', '拒单数', 'integer'], ['average_cash_weight', '平均现金', 'percent'],
  ['slippage_scenario', '滑点场景', 'text'],
] as const

export function metricText(value: unknown, format: string) {
  if (typeof value === 'string') return value
  if (typeof value !== 'number' || !Number.isFinite(value)) return '—'
  if (format === 'percent') return formatPercent(value)
  return format === 'integer' ? formatNumber(value) : value.toFixed(3)
}

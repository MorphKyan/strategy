<script setup lang="ts">
import { ArrowUpRight, BriefcaseBusiness, ChartNoAxesCombined, Layers3, ListFilter, SlidersHorizontal } from '@lucide/vue'
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { endpoint, formatNumber, formatPercent, kindLabel, performanceClass, portfolioQuery, useResource, useTemporary, type Overview } from './api'

const include = useTemporary()
const { data, loading, error } = useResource<Overview>(() => endpoint('/api/overview', { include_temporary: include.value }))

const metrics = computed(() => [
  { label: '组合', value: data.value?.portfolios.length, icon: BriefcaseBusiness },
  { label: '策略配置', value: data.value?.configCount, icon: SlidersHorizontal },
  { label: '策略类型', value: data.value?.strategyCount, icon: Layers3 },
  { label: '正式回测', value: data.value?.runCount, icon: ChartNoAxesCombined },
])
</script>

<template>
  <div class="page-stack" :aria-busy="loading">
    <p v-if="error" class="notice" role="alert">{{ error }}</p>
    <div class="metrics-grid" aria-label="工作区指标">
      <section v-for="metric in metrics" :key="metric.label" class="metric">
        <span class="metric-icon"><component :is="metric.icon" :size="17" :stroke-width="1.8" aria-hidden="true" /></span>
        <div><p class="metric-label">{{ metric.label }}</p><p class="metric-value">{{ formatNumber(metric.value ?? null) }}</p></div>
      </section>
    </div>

    <div v-if="data" class="overview-grid">
      <section class="panel">
        <header class="panel-heading"><h1>组合</h1><RouterLink class="text-link quiet-link" :to="{ name: 'portfolios' }">查看全部 <ArrowUpRight :size="15" aria-hidden="true" /></RouterLink></header>
        <div v-if="data.portfolios.length" class="table-scroll">
          <table class="data-table">
            <thead><tr><th scope="col">组合</th><th scope="col">净值日期</th><th scope="col" class="numeric">成立以来</th><th scope="col" class="arrow-cell"><span class="sr-only">查看详情</span></th></tr></thead>
            <tbody>
              <tr v-for="portfolio in data.portfolios" :key="`${portfolio.kind}:${portfolio.id}`">
                <td>
                  <RouterLink class="portfolio-link" :to="{ name: 'portfolio', query: portfolioQuery(portfolio) }">
                    <span class="kind" :class="portfolio.kind">{{ kindLabel(portfolio.kind) }}</span>
                    <span class="portfolio-name" :title="portfolio.id">{{ portfolio.id }}</span>
                  </RouterLink>
                </td>
                <td><span>{{ portfolio.asOf ?? '—' }}</span><span v-if="(portfolio.businessDaysBehind ?? 0) >= 3" class="date-lag">滞后 {{ portfolio.businessDaysBehind }} 个工作日</span></td>
                <td class="numeric" :class="performanceClass(portfolio.returnSinceStart)">{{ formatPercent(portfolio.returnSinceStart) }}</td>
                <td class="arrow-cell"><RouterLink class="details-link" :to="{ name: 'portfolio', query: portfolioQuery(portfolio) }" :aria-label="`查看 ${portfolio.id}`"><ArrowUpRight :size="17" aria-hidden="true" /></RouterLink></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="empty-state"><BriefcaseBusiness :size="22" /><p>暂无实盘或模拟组合</p></div>
      </section>

      <div class="page-stack">
        <section class="panel">
          <header class="panel-heading"><h2>最近回测</h2><RouterLink class="text-link quiet-link" :to="{ name: 'backtests' }">回测分析 <ArrowUpRight :size="15" aria-hidden="true" /></RouterLink></header>
          <ul v-if="data.recentRuns.length" class="run-list">
            <li v-for="run in data.recentRuns" :key="run.id">
              <div class="run-description"><RouterLink class="text-link" :title="run.id" :to="{ name: 'backtests', query: { id: run.id } }"><strong>{{ run.id }}</strong></RouterLink><span>{{ run.date || '日期未知' }} · 回撤 {{ formatPercent(run.maxDrawdown) }}</span></div>
              <div class="run-return"><strong :class="performanceClass(run.annualizedReturn)">{{ formatPercent(run.annualizedReturn) }}</strong><span>年化</span></div>
            </li>
          </ul>
          <div v-else class="empty-state"><ListFilter :size="22" /><p>{{ include ? '暂无可读取的回测' : '暂无正式回测' }}</p></div>
        </section>

        <section class="panel">
          <header class="panel-heading"><h2>策略配置分布</h2><span v-if="data.strategyCount > 5" class="table-count">前 5 类</span></header>
          <ul v-if="data.strategies.length" class="strategy-list">
            <li v-for="strategy in data.strategies" :key="strategy.name">
              <span class="strategy-name" :title="strategy.name">{{ strategy.name }}</span>
              <span class="strategy-count">{{ strategy.count }}</span>
              <div class="distribution" role="img" :aria-label="`${strategy.name} 占 ${formatPercent(strategy.count / data.configCount)}`">
                <div :style="{ width: `${strategy.count / data.configCount * 100}%` }" />
              </div>
            </li>
          </ul>
          <div v-else class="empty-state"><p>暂无策略配置</p></div>
        </section>
      </div>
    </div>
    <p v-else-if="loading" class="loading-state" role="status">正在读取工作区数据…</p>
  </div>
</template>

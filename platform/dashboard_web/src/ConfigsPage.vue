<script setup lang="ts">
import { computed, ref } from 'vue'
import { endpoint, useResource, type Row } from './api'
import DataTable from './DataTable.vue'

type Config = { id: string; name: string; strategy: string }
type Detail = { assets: Row[]; params: Row[]; yaml: string }
const strategy = ref('')
const selected = ref('')
const configs = useResource<Config[]>(() => '/api/configs')
const strategies = computed(() => [...new Set(configs.data.value?.map(item => item.strategy))].sort())
const choices = computed(() => (configs.data.value ?? []).filter(item => !strategy.value || item.strategy === strategy.value))
const current = computed(() => choices.value.find(item => item.id === selected.value) ?? choices.value[0])
const detail = useResource<Detail>(() => current.value && endpoint('/api/config', { id: current.value.id }))
</script>

<template>
  <div class="page-stack" :aria-busy="configs.loading.value || detail.loading.value">
    <header class="page-heading"><h1>策略配置</h1></header>
    <div v-if="configs.data.value?.length" class="filter-bar">
      <label class="field"><span>策略类型</span><select v-model="strategy"><option value="">全部</option><option v-for="item in strategies" :key="item">{{ item }}</option></select></label>
      <label class="field grow-field"><span>配置文件</span><select :value="current?.id" @change="selected = ($event.target as HTMLSelectElement).value">
        <option v-for="item in choices" :key="item.id" :value="item.id">{{ item.name }}</option>
      </select></label>
    </div>
    <p v-if="configs.error.value || detail.error.value" class="notice" role="alert">{{ configs.error.value || detail.error.value }}</p>
    <p v-if="configs.loading.value || detail.loading.value" class="loading-state" role="status">正在读取配置…</p>
    <div v-else-if="!configs.data.value?.length && !configs.error.value" class="panel empty-state"><p>暂无策略配置</p></div>
    <template v-if="detail.data.value && current">
      <p class="context-line"><strong>{{ current.strategy }}</strong><code>{{ current.id }}</code></p>
      <div class="equal-grid">
        <DataTable title="资产篮子" :rows="detail.data.value.assets" />
        <DataTable title="策略参数" :rows="detail.data.value.params" />
      </div>
      <details class="panel disclosure"><summary>完整 YAML</summary><pre>{{ detail.data.value.yaml }}</pre></details>
    </template>
  </div>
</template>

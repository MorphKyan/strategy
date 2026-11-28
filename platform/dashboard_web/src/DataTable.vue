<script setup lang="ts">
import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { formatQuantity, type Row } from './api'
import Button from './Button.vue'

type Column = { key: string; label?: string; format?: (value: unknown) => string; numeric?: boolean }
const props = withDefaults(defineProps<{
  title: string
  rows: Row[]
  columns?: Column[]
  empty?: string
  pageSize?: number
}>(), { empty: '暂无记录', pageSize: 30 })

const columns = computed<Column[]>(() => props.columns ?? [...new Set(props.rows.flatMap(Object.keys))].map(key => ({ key })))
const page = ref(0)
const sort = ref<{ key: string; descending: boolean }>()
const pages = computed(() => Math.ceil(props.rows.length / props.pageSize))
const displayed = computed(() => {
  let list = props.rows
  const by = sort.value
  if (by) {
    list = [...list].sort((left, right) => {
      const a = left[by.key]
      const b = right[by.key]
      if (a == null) return b == null ? 0 : 1
      if (b == null) return -1
      const order = typeof a === 'number' && typeof b === 'number' ? a - b : String(a).localeCompare(String(b), 'zh-CN', { numeric: true })
      return by.descending ? -order : order
    })
  }
  return list.slice(page.value * props.pageSize, (page.value + 1) * props.pageSize)
})
watch(() => props.rows, () => {
  page.value = 0
  if (!columns.value.some(column => column.key === sort.value?.key)) sort.value = undefined
})
function order(key: string) {
  sort.value = { key, descending: sort.value?.key === key && !sort.value.descending }
  page.value = 0
}
function cell(value: unknown) {
  if (value == null || value === '') return '—'
  if (typeof value === 'number') return formatQuantity(value)
  if (typeof value === 'object') return JSON.stringify(value)
  if (typeof value === 'string') return value.replace(/^(\d{4}-\d{2}-\d{2})T00:00:00\.000$/, '$1')
  return String(value)
}
</script>

<template>
  <section class="panel">
    <header class="panel-heading"><h2>{{ title }}</h2><span v-if="rows.length" class="table-count">{{ rows.length }} 条</span></header>
    <div v-if="rows.length" class="table-scroll" tabindex="0" :aria-label="title">
      <table class="data-table generic-table">
        <thead><tr>
          <th v-for="column in columns" :key="column.key" scope="col" :class="{ numeric: column.numeric }"
              :aria-sort="sort?.key === column.key ? (sort.descending ? 'descending' : 'ascending') : undefined">
            <button type="button" class="sort-button" @click="order(column.key)">
              {{ column.label ?? column.key }}
              <component :is="sort.descending ? ArrowDown : ArrowUp" v-if="sort?.key === column.key" :size="13" aria-hidden="true" />
            </button>
          </th>
        </tr></thead>
        <tbody><tr v-for="(row, index) in displayed" :key="index">
          <td v-for="column in columns" :key="column.key" :class="{ numeric: column.numeric }">
            <slot :name="column.key" :row="row" :value="row[column.key]">{{ column.format ? column.format(row[column.key]) : cell(row[column.key]) }}</slot>
          </td>
        </tr></tbody>
      </table>
    </div>
    <div v-else class="empty-state"><p>{{ empty }}</p></div>
    <footer v-if="pages > 1" class="table-footer">
      <span>第 {{ page + 1 }} / {{ pages }} 页</span>
      <Button size="icon" variant="ghost" aria-label="上一页" :disabled="page === 0" @click="page--"><ChevronLeft /></Button>
      <Button size="icon" variant="ghost" aria-label="下一页" :disabled="page + 1 === pages" @click="page++"><ChevronRight /></Button>
    </footer>
  </section>
</template>

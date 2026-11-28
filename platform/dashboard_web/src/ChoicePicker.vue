<script setup lang="ts">
import { Search, X } from '@lucide/vue'
import { computed, ref } from 'vue'

const props = defineProps<{ choices: string[]; max: number; title: string }>()
const selected = defineModel<string[]>({ required: true })
const query = ref('')
const page = ref(0)
const pageSize = 24
const filtered = computed(() => {
  const terms = query.value.trim().toLowerCase().split(/\s+/)
  return props.choices.filter(choice => terms.every(term => choice.toLowerCase().includes(term)))
})
const visible = computed(() => filtered.value.slice(page.value * pageSize, (page.value + 1) * pageSize))
</script>

<template>
  <section class="panel choice-picker">
    <header class="panel-heading"><h2>{{ title }}</h2><span class="table-count">已选 {{ selected.length }} / {{ max }}</span></header>
    <div v-if="selected.length" class="choice-tags">
      <button v-for="item in selected" :key="item" type="button" :aria-label="'移除 ' + item" @click="selected = selected.filter(value => value !== item)">
        <span :title="item">{{ item }}</span><X :size="14" aria-hidden="true" />
      </button>
    </div>
    <details class="choice-details">
      <summary>调整选择</summary>
      <div class="search-field">
        <Search :size="16" aria-hidden="true" />
        <input v-model="query" type="search" aria-label="筛选可选项" placeholder="输入关键词筛选" @input="page = 0">
      </div>
      <div v-if="visible.length" class="choice-options">
        <label v-for="item in visible" :key="item" class="check-field" :title="item">
          <input v-model="selected" type="checkbox" :value="item" :disabled="selected.length >= max && !selected.includes(item)">
          <span>{{ item }}</span>
        </label>
      </div>
      <p v-else class="muted">暂无匹配项</p>
      <div v-if="filtered.length > pageSize" class="pagination">
        <button type="button" class="text-link" :disabled="page === 0" @click="page--">上一页</button>
        <span class="muted">第 {{ page + 1 }} / {{ Math.ceil(filtered.length / pageSize) }} 页</span>
        <button type="button" class="text-link" :disabled="(page + 1) * pageSize >= filtered.length" @click="page++">下一页</button>
      </div>
    </details>
  </section>
</template>

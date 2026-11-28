<script setup lang="ts">
import { periods, type Mode } from './api'

defineProps<{ benchmarkOptions?: { value: string; label: string }[]; showLog?: boolean }>()
const period = defineModel<string>('period', { required: true })
const mode = defineModel<Mode>('mode', { required: true })
const benchmark = defineModel<string>('benchmark')
const logarithmic = defineModel<boolean>('logarithmic')
</script>

<template>
  <div class="filter-bar">
    <label class="field"><span>区间</span><select v-model="period" aria-label="区间"><option v-for="item in periods" :key="item">{{ item }}</option></select></label>
    <label class="field"><span>显示</span><select v-model="mode" aria-label="显示"><option value="nav">净值</option><option value="return">收益率</option></select></label>
    <label v-if="benchmarkOptions" class="field grow-field"><span>基准对比</span>
      <select v-model="benchmark" aria-label="基准对比"><option value="">无</option><option v-for="item in benchmarkOptions" :key="item.value" :value="item.value">{{ item.label }}</option></select>
    </label>
    <label v-if="showLog" class="check-field"><input v-model="logarithmic" type="checkbox" :disabled="mode === 'return'"> 对数坐标</label>
    <slot />
  </div>
</template>

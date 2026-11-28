<script setup lang="ts">
import type { Figure, NamedTable } from './api'
import DataTable from './DataTable.vue'
import PlotChart from './PlotChart.vue'

defineProps<{ charts?: Figure[]; tables?: NamedTable[]; note?: string; empty?: string }>()
</script>

<template>
  <p v-if="note" class="notice" role="status">{{ note }}</p>
  <div v-if="charts?.length" class="analysis-grid">
    <section v-for="figure in charts" :key="figure.title" class="panel" :class="{ 'wide-chart': (figure.layout.height ?? 0) >= 400 || /热力图/.test(figure.title) }">
      <header class="panel-heading"><h2>{{ figure.title }}</h2></header>
      <PlotChart :title="figure.title" :data="figure.data" :layout="figure.layout" />
    </section>
  </div>
  <DataTable v-for="table in tables" :key="table.title" :title="table.title" :rows="table.rows" />
  <div v-if="!note && !charts?.length && !tables?.length && empty" class="panel empty-state"><p>{{ empty }}</p></div>
</template>

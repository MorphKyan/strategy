<script setup lang="ts">
defineProps<{ loading?: boolean; error?: string; label?: string }>()
</script>

<template>
  <p v-if="error" class="notice" role="alert">{{ error }}</p>
  <p v-else-if="loading" class="loading-state" role="status">{{ label ?? '正在读取数据…' }}</p>
</template>

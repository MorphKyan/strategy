<script setup lang="ts">
import {
  ArrowDownUp, BriefcaseBusiness, ChartCandlestick, ChartNoAxesCombined, LayoutDashboard, LineChart,
  PanelLeftClose, PanelLeftOpen, RefreshCw, Settings2, X,
} from '@lucide/vue'
import { computed, nextTick, onBeforeUnmount, onMounted, provide, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import Button from './Button.vue'

const route = useRoute()
const collapsed = ref(false)
const mobileOpen = ref(false)
const refresh = ref(0)
const includeTemporary = ref(false)
const rail = ref<HTMLElement>()
const toolbar = ref<HTMLElement>()
const mobileLayout = window.matchMedia('(max-width: 720px)')
provide('refresh', refresh)
provide('includeTemporary', includeTemporary)

function syncViewport() {
  if (!mobileLayout.matches) mobileOpen.value = false
}
onMounted(() => mobileLayout.addEventListener('change', syncViewport))
onBeforeUnmount(() => mobileLayout.removeEventListener('change', syncViewport))

async function openNav() {
  mobileOpen.value = true
  await nextTick()
  rail.value?.querySelector<HTMLElement>('.rail-close')?.focus()
}
async function closeNav(restore = true) {
  if (!mobileOpen.value) return
  mobileOpen.value = false
  if (restore) {
    await nextTick()
    toolbar.value?.querySelector<HTMLElement>('.mobile-toggle')?.focus()
  }
}
watch(() => route.fullPath, () => { void closeNav(false) })

const navigation = [
  [{ name: 'overview', label: '概览', icon: LayoutDashboard }],
  [
    { name: 'portfolios', label: '组合总览', icon: BriefcaseBusiness },
    { name: 'portfolio', label: '组合详情', icon: LineChart },
    { name: 'market', label: '市场数据', icon: ChartCandlestick },
  ],
  [
    { name: 'backtests', label: '回测分析', icon: ChartNoAxesCombined },
    { name: 'compare', label: '回测对比', icon: ArrowDownUp },
    { name: 'configs', label: '策略配置', icon: Settings2 },
  ],
]
const active = computed(() => navigation.flat().find(item => item.name === route.name))
watch(active, item => {
  document.title = item ? item.label + ' · Platform' : 'Platform'
}, { immediate: true })
</script>

<template>
  <div class="workspace" :class="{ 'rail-compact': collapsed, 'mobile-open': mobileOpen }" @keydown.esc="closeNav()">
    <button v-if="mobileOpen" class="menu-backdrop" tabindex="-1" aria-label="关闭导航" @click="closeNav()" />
    <aside id="workspace-navigation" ref="rail" class="rail">
      <div class="rail-top">
        <RouterLink class="brand" :to="{ name: 'overview' }" aria-label="Platform 首页" @click="closeNav()">
          <span class="brand-mark" aria-hidden="true"><ChartNoAxesCombined :size="18" :stroke-width="2" /></span>
          <span class="brand-label">Platform</span>
        </RouterLink>
        <Button class="rail-close" size="icon" variant="ghost" aria-label="关闭导航" @click="closeNav()"><X /></Button>
      </div>
      <nav class="rail-nav" aria-label="主导航">
        <div v-for="group in navigation" :key="group[0]?.name" class="nav-group">
          <RouterLink
            v-for="item in group" :key="item.name" :to="{ name: item.name }"
            :class="{ 'selected-route': route.name === item.name }"
            :aria-current="route.name === item.name ? 'page' : undefined"
            :aria-label="item.label" :title="collapsed ? item.label : undefined"
            @click="closeNav()"
          >
            <component :is="item.icon" :size="19" :stroke-width="1.75" aria-hidden="true" />
            <span>{{ item.label }}</span>
          </RouterLink>
        </div>
      </nav>
      <div class="rail-footer">
        <label class="check-field" title="加载临时回测">
          <input v-model="includeTemporary" type="checkbox" aria-label="加载临时回测">
          <span>加载临时回测</span>
        </label>
      </div>
    </aside>

    <div class="workspace-main" :inert="mobileOpen">
      <a class="skip-link" href="#main-content">跳到主要内容</a>
      <header ref="toolbar" class="toolbar">
        <Button
          class="desktop-toggle" variant="ghost" size="icon"
          :aria-label="collapsed ? '展开侧栏' : '收起侧栏'" :aria-expanded="!collapsed"
          aria-controls="workspace-navigation" @click="collapsed = !collapsed"
        ><PanelLeftOpen v-if="collapsed" /><PanelLeftClose v-else /></Button>
        <Button
          class="mobile-toggle" variant="ghost" size="icon" aria-label="打开导航"
          :aria-expanded="mobileOpen" aria-controls="workspace-navigation" @click="openNav"
        ><PanelLeftOpen /></Button>
        <span class="toolbar-title">Platform</span>
        <div class="toolbar-actions">
          <Button variant="outline" @click="refresh++"><RefreshCw aria-hidden="true" />刷新数据</Button>
        </div>
      </header>
      <main id="main-content" class="content" tabindex="-1"><RouterView /></main>
    </div>
  </div>
</template>

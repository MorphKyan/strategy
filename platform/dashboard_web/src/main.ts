import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import OverviewPage from './OverviewPage.vue'
import './style.css'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'overview', component: OverviewPage },
    { path: '/portfolios', name: 'portfolios', component: () => import('./PortfoliosPage.vue') },
    { path: '/portfolio', name: 'portfolio', component: () => import('./PortfolioPage.vue') },
    { path: '/market', name: 'market', component: () => import('./MarketPage.vue') },
    { path: '/backtests', name: 'backtests', component: () => import('./BacktestsPage.vue') },
    { path: '/compare', name: 'compare', component: () => import('./ComparePage.vue') },
    { path: '/configs', name: 'configs', component: () => import('./ConfigsPage.vue') },
  ],
  scrollBehavior: (to, from, position) => position ?? (to.path === from.path ? false : { top: 0 }),
})

router.beforeEach(to => {
  if ('theme' in to.query) {
    const query = { ...to.query }
    delete query.theme
    return { path: to.path, query, hash: to.hash, replace: true }
  }
})

createApp(App).use(router).mount('#app')

<template>
  <div class="discovery">
    <section class="hero">
      <div>
        <span class="eyebrow">校园闲置</span>
        <h1>闲置再出发，<br><em>好物遇见你。</em></h1>
        <p>书籍、数码和生活用品，在同一座校园找到下一位主人。浏览闲置、联系同学，让每一次交接更轻松。</p>
        <form class="search" @submit.prevent="search">
          <el-input v-model="keyword" aria-label="搜索闲置" placeholder="搜索书籍、键盘、运动用品…" clearable />
          <el-button type="primary" native-type="submit">搜索闲置</el-button>
        </form>
        <el-button round @click="router.push('/items?publish=1')">发布我的闲置</el-button>
      </div>
      <aside class="guide">
        <span>让好物继续被使用</span>
        <ol><li><b>01 浏览发现</b><p>按分类寻找适合自己的闲置</p></li><li><b>02 联系同学</b><p>确认成色、价格与交接地点</p></li><li><b>03 完成交接</b><p>交换有记录，完成后双方评价</p></li></ol>
      </aside>
    </section>
    <section class="metrics" aria-label="平台数据">
      <article><strong>{{ stats.users }}</strong><span>校园成员</span></article>
      <article><strong>{{ stats.items }}</strong><span>在架闲置</span></article>
      <article><strong>{{ stats.completed_transactions }}</strong><span>已完成交易</span></article>
    </section>
    <section>
      <div class="heading"><div><small>按分类逛逛</small><h2>找到你需要的好物</h2></div><router-link to="/items">全部闲置 →</router-link></div>
      <div class="categories"><button v-for="category in categories" :key="category" @click="router.push({ path: '/items', query: { category } })">{{ category }} <span>↗</span></button></div>
    </section>
    <section>
      <div class="heading"><div><small>按发布时间排序</small><h2>最新闲置</h2></div><router-link to="/items">查看更多 →</router-link></div>
      <el-skeleton v-if="loading" :rows="6" animated />
      <el-alert v-else-if="failed" title="暂时无法加载闲置，请稍后重试" type="error" :closable="false"><el-button @click="load">重新加载</el-button></el-alert>
      <div v-else-if="items.length" class="item-grid">
        <router-link v-for="item in items" :key="item.id" :to="'/items/' + item.id" class="item-card">
          <img :src="item.images?.[0] || '/default-item.svg'" :alt="item.title" @error="imageFallback">
          <div class="card-body"><span class="chip">{{ item.category }}</span><h3>{{ item.title }}</h3><p>{{ item.condition }} · {{ item.location_campus || '校内面交' }}</p><div class="card-bottom"><strong>{{ price(item) }}</strong><span>{{ item.user?.username }}</span></div></div>
        </router-link>
      </div>
      <el-empty v-else description="还没有在架闲置，发布第一件好物吧"><el-button type="primary" @click="router.push('/items?publish=1')">发布闲置</el-button></el-empty>
    </section>
  </div>
</template>
<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { itemsAPI } from '@/api/items'
import { metaAPI } from '@/api/meta'
const router = useRouter()
const keyword = ref('')
const loading = ref(true)
const failed = ref(false)
const items = ref([])
const stats = ref({ users: '—', items: '—', completed_transactions: '—' })
const categories = ['电子产品', '书籍', '家居用品', '运动器材', '服装', '其他']
const search = () => router.push({ path: '/items', query: { search: keyword.value.trim() } })
const price = (item) => item.transaction_type === '租赁' ? '¥' + item.rental_price_day + '/天' : item.sale_price ? '¥' + item.sale_price : '物物交换'
const imageFallback = (event) => {
  if (!event.target.src.endsWith('/default-item.svg')) event.target.src = '/default-item.svg'
}
const load = async () => {
  loading.value = true
  failed.value = false
  const [a, b] = await Promise.allSettled([metaAPI.getPlatformStats(), itemsAPI.getItems({ per_page: 6, sort_by: 'latest' })])
  if (a.status === 'fulfilled') stats.value = a.value.data
  if (b.status === 'fulfilled') items.value = b.value.data.items || []
  else failed.value = true
  loading.value = false
}
onMounted(load)
</script>
<style scoped>
.discovery { display: grid; gap: 48px; }
.hero { padding: 52px; border: 1px solid var(--ink); border-radius: 10px; box-shadow: 6px 6px 0 var(--accent); background: var(--ink); color: white; display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr); gap: 44px; align-items: center; }
.eyebrow { color: var(--lime); font-size: 12px; letter-spacing: .1em; }
h1 { font-size: clamp(32px, 4.5vw, 62px); line-height: 1.2; margin: 22px 0; }
h1 em { color: var(--accent); font-style: normal; }
.hero p { line-height: 1.8; opacity: .75; }
.search { display: flex; gap: 10px; margin: 26px 0 18px; }
.guide { padding: 28px; border: 1px solid #ffffff30; border-radius: 8px; background: #ffffff0b; }
.guide > span { color: var(--lime); }
.guide ol { padding: 0; list-style: none; }
.guide li { margin-top: 25px; }
.guide p { margin-bottom: 0; font-size: 14px; }
.metrics { display: grid; grid-template-columns: repeat(3, 1fr); border: 1px solid var(--line); border-radius: 8px; background: var(--paper); }
.metrics article { padding: 26px; display: grid; gap: 8px; text-align: center; }
.metrics strong { font-size: 32px; color: var(--ink); }
.metrics span, .card-body p { color: var(--muted); font-size: 14px; }
.heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 22px; }
.heading small { color: var(--ink); background: var(--accent); padding: 3px 8px; }
.heading h2 { margin: 8px 0 0; font-size: 27px; }
.heading a { white-space: nowrap; color: var(--ink); }
.categories { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 12px; }
.categories button { padding: 22px 14px; border: 1px solid var(--line); border-radius: 6px; background: var(--paper); color: var(--ink); cursor: pointer; font: inherit; }
.categories button:hover { background: var(--lime); }
.categories span { margin-left: 8px; }
.item-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 22px; }
.item-card { display: block; color: var(--ink); text-decoration: none; background: var(--paper); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; transition: transform .2s; }
.item-card:hover { transform: translateY(-3px); border-color: var(--ink); box-shadow: 3px 3px 0 var(--ink); }
.item-card img { width: 100%; height: 200px; object-fit: cover; background: #f1f1ed; }
.card-body { padding: 22px; }
.card-body h3 { overflow-wrap: anywhere; }
.chip { background: var(--lime); border-radius: 5px; padding: 4px 8px; font-size: 12px; }
.card-bottom { display: flex; justify-content: space-between; gap: 10px; }
.card-bottom strong { color: var(--coral); }
.card-bottom span { font-size: 13px; color: var(--muted); }
@media(max-width: 900px) { .hero { grid-template-columns: 1fr; padding: 32px; } .categories { grid-template-columns: repeat(3, 1fr); } .item-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media(max-width: 540px) { .hero { padding: 24px; } .search { flex-direction: column; } .item-grid { grid-template-columns: 1fr; } .metrics article { padding: 18px 8px; } .metrics strong { font-size: 25px; } .heading h2 { font-size: 22px; } .categories { grid-template-columns: repeat(2, 1fr); } }
</style>

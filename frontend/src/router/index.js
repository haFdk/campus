import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const Layout = () => import('@/layout/index.vue')
const Login = () => import('@/views/auth/Login.vue')
const Register = () => import('@/views/auth/Register.vue')
const Home = () => import('@/views/Home.vue')
const Profile = () => import('@/views/profile/Profile.vue')
const Items = () => import('@/views/items/Items.vue')
const ItemDetail = () => import('@/views/items/ItemDetail.vue')
const Messages = () => import('@/views/messages/Messages.vue')
const Transactions = () => import('@/views/transactions/Transactions.vue')
const Reviews = () => import('@/views/reviews/Reviews.vue')

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { title: '登录', requiresGuest: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: Register,
    meta: { title: '注册', requiresGuest: true }
  },
  {
    path: '/',
    component: Layout,
    redirect: '/home',
    children: [
      { path: ':pathMatch(.*)*', component: () => import('@/views/NotFound.vue'), meta: { title: '页面不存在' } },
      {
        path: 'home',
        name: 'Home',
        component: Home,
        meta: { title: '首页' }
      },
      {
        path: 'profile',
        name: 'Profile',
        component: Profile,
        meta: { title: '个人资料', requiresAuth: true }
      },
      {
        path: 'items',
        name: 'Items',
        component: Items,
        meta: { title: '校园闲置' }
      },
      {
        path: 'items/:id',
        name: 'ItemDetail',
        component: ItemDetail,
        meta: { title: '物品详情' }
      },
      {
        path: 'messages',
        name: 'Messages',
        component: Messages,
        meta: { title: '消息中心', requiresAuth: true }
      },
      {
        path: 'transactions',
        name: 'Transactions',
        component: Transactions,
        meta: { title: '交易记录', requiresAuth: true }
      },
      {
        path: 'reviews',
        name: 'Reviews',
        component: Reviews,
        meta: { title: '评价管理', requiresAuth: true }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  document.title = `${to.meta.title || '发现'} · 校园闲置交易平台`

  // 需要登录的页面
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
    return
  }

  // 已登录用户访问登录/注册页面
  if (to.meta.requiresGuest && authStore.isAuthenticated) {
    next('/')
    return
  }

  next()
})

export default router

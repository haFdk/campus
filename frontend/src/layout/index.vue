<template>
  <div class="app-shell">
    <header class="site-header">
      <div class="header-inner">
        <button class="brand" type="button" aria-label="返回首页" @click="router.push('/home')">
          <span class="brand-mark">C</span>
          <span class="brand-copy">
            <strong>校园闲置</strong>
          </span>
        </button>

        <nav class="primary-nav" aria-label="主导航">
          <router-link to="/home">发现</router-link>
          <router-link to="/items">闲置</router-link>
        </nav>

        <div class="user-actions">
          <template v-if="authStore.isAuthenticated">
            <button
              class="icon-button"
              type="button"
              aria-label="消息中心"
              @click="router.push('/messages')"
            >
              <el-badge :value="unreadCount" :hidden="unreadCount === 0">
                <el-icon><Message /></el-icon>
              </el-badge>
            </button>
            <el-dropdown @command="handleUserCommand">
              <button class="user-chip" type="button">
                <el-avatar :size="34" :src="authStore.user?.avatar_url">
                  {{ userInitial }}
                </el-avatar>
                <span>{{ authStore.user?.username || '同学' }}</span>
                <el-icon><ArrowDown /></el-icon>
              </button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="profile">个人主页</el-dropdown-item>
                  <el-dropdown-item command="transactions">交易进度</el-dropdown-item>
                  <el-dropdown-item command="reviews">评价记录</el-dropdown-item>
                  <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
          <template v-else>
            <el-button text @click="router.push('/login')">登录</el-button>
            <el-button type="primary" round @click="router.push('/register')">
              加入社区
            </el-button>
          </template>
        </div>
      </div>
    </header>

    <main class="site-main">
      <router-view />
    </main>

    <footer class="site-footer">
      <div>
        <strong>校园闲置</strong>
        <span>让闲置在校园里找到下一位主人。</span>
      </div>
      <span>校内沟通 · 闲置流转</span>
    </footer>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowDown, Message } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import { messagesAPI } from '@/api/messages'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const unreadCount = ref(0)
let unreadTimer = null

const userInitial = computed(() =>
  (authStore.user?.username || '同').slice(0, 1).toUpperCase()
)

const refreshUnreadCount = async () => {
  if (!authStore.isAuthenticated) return
  try {
    const { data } = await messagesAPI.getUnreadCount()
    unreadCount.value = data.unread_count || 0
  } catch {
    unreadCount.value = 0
  }
}

const handleUserCommand = async (command) => {
  if (command !== 'logout') {
    router.push(`/${command}`)
    return
  }
  try {
    await ElMessageBox.confirm('确认退出当前账号？', '退出登录', {
      confirmButtonText: '退出',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await authStore.logout()
    router.push('/home')
  } catch {
    // User cancelled.
  }
}

onMounted(async () => {
  await authStore.init()
  await refreshUnreadCount()
  unreadTimer = window.setInterval(refreshUnreadCount, 30000)
})

onUnmounted(() => {
  if (unreadTimer) window.clearInterval(unreadTimer)
})
</script>

<style lang="scss" scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.site-header {
  position: sticky;
  top: 0;
  z-index: 100;
  padding: 12px 24px;
  border-bottom: 1px solid rgba(23, 23, 23, 0.1);
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(18px);
}

.header-inner {
  width: min(1180px, 100%);
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 24px;
}

.brand {
  border: 0;
  padding: 0;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  width: fit-content;
  color: var(--ink);
  background: transparent;
  cursor: pointer;
  text-align: left;
}

.brand-mark {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: 6px;
  color: #fff;
  background: var(--ink);
  font: 800 20px/1 var(--font-display);
  box-shadow: 4px 4px 0 var(--lime);
}

.brand-copy {
  display: grid;
  line-height: 1.1;

  strong {
    font-size: 15px;
    letter-spacing: 0.04em;
  }

  small {
    margin-top: 4px;
    color: var(--muted);
    font-size: 10px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }
}

.primary-nav {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.72);

  a {
    padding: 8px 17px;
    border-radius: 8px;
    color: var(--muted);
    font-weight: 650;
    text-decoration: none;
    transition: 180ms ease;
  }

  a:hover {
    color: var(--ink);
  }

  a.router-link-active {
    color: var(--ink);
    background: var(--accent);
  }
}

.user-actions {
  justify-self: end;
  display: flex;
  align-items: center;
  gap: 8px;
}

.icon-button,
.user-chip {
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.8);
  cursor: pointer;
}

.icon-button {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: var(--ink);
  font-size: 18px;
}

.user-chip {
  padding: 3px 10px 3px 3px;
  display: flex;
  align-items: center;
  gap: 8px;
  border-radius: 8px;
  color: var(--ink);
  font-weight: 650;
}

.site-main {
  flex: 1;
  width: min(1220px, 100%);
  margin: 0 auto;
  padding: 28px 20px 56px;
}

.site-footer {
  width: min(1180px, calc(100% - 40px));
  margin: 0 auto;
  padding: 24px 0 32px;
  border-top: 1px solid var(--line);
  display: flex;
  justify-content: space-between;
  gap: 16px;
  color: var(--muted);
  font-size: 13px;

  div {
    display: flex;
    gap: 12px;
  }

  strong {
    color: var(--ink);
  }
}

@media (max-width: 860px) {
  .site-header {
    padding: 10px 14px;
  }

  .header-inner {
    grid-template-columns: 1fr auto;
  }

  .primary-nav {
    grid-row: 2;
    grid-column: 1 / -1;
    width: 100%;
    justify-content: space-between;

    a {
      flex: 1;
      padding-inline: 8px;
      text-align: center;
    }
  }

  .user-chip > span:not(.el-avatar),
  .brand-copy small {
    display: none;
  }
}

@media (max-width: 540px) {
  .site-main {
    padding: 20px 12px 40px;
  }

  .brand-copy {
    display: none;
  }

  .site-footer {
    flex-direction: column;

    div {
      display: grid;
      gap: 4px;
    }
  }
}
</style>

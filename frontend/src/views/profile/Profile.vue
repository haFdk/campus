<template>
  <div class="profile-page">
    <section class="profile-hero">
      <div class="profile-identity">
        <el-avatar :size="92" :src="form.avatar_url">
          {{ form.username?.slice(0, 1) }}
        </el-avatar>
        <div>
          <span class="profile-label">Campus Loop member</span>
          <h1>{{ form.username || '校园用户' }}</h1>
          <p>{{ form.major || '还没有填写专业' }} · {{ form.grade || '还没有填写年级' }}</p>
        </div>
      </div>
      <el-button round @click="editing = !editing">
        <el-icon><Edit /></el-icon>
        {{ editing ? '取消编辑' : '编辑资料' }}
      </el-button>
    </section>

    <section class="stat-grid">
      <article>
        <router-link to="/items?mine=1">我的闲置 →</router-link>
        <strong>{{ stats.items_count }}</strong>
        <small>查看和管理我发布的物品</small>
      </article>
      <article>
        <span>交易记录</span>
        <strong>{{ stats.transactions_count }}</strong>
        <small>包含发起与承接</small>
      </article>
    </section>

    <section class="profile-grid">
      <el-card class="info-card">
        <template #header>
          <div class="card-title">
            <div>
              <span>个人信息</span>
              <small>这些信息会帮助其他同学了解你</small>
            </div>
            <el-tag type="success" effect="plain">已登录</el-tag>
          </div>
        </template>

        <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
          <div class="form-grid">
            <el-form-item label="用户名" prop="username">
              <el-input v-model="form.username" :disabled="!editing" />
            </el-form-item>
            <el-form-item label="邮箱">
              <el-input v-model="form.email" disabled />
            </el-form-item>
            <el-form-item label="专业 / 方向">
              <el-input v-model="form.major" :disabled="!editing" placeholder="例如：计算机科学" />
            </el-form-item>
            <el-form-item label="年级 / 身份">
              <el-input v-model="form.grade" :disabled="!editing" placeholder="例如：大三" />
            </el-form-item>
          </div>
          <el-form-item v-if="editing" label="头像链接">
            <el-input v-model="form.avatar_url" placeholder="https://..." />
          </el-form-item>
          <div v-if="editing" class="form-actions">
            <el-button type="primary" :loading="saving" @click="saveProfile">保存修改</el-button>
          </div>
        </el-form>
      </el-card>

      <aside class="security-panel">
        <div class="security-icon"><Lock /></div>
        <span>账号安全</span>
        <h2>定期更新密码</h2>
        <p>请勿在公开描述或消息里发送身份证号、银行卡等敏感信息。</p>
        <el-button type="primary" plain @click="showPasswordDialog = true">
          修改密码
        </el-button>
      </aside>
    </section>

    <ChangePasswordDialog
      v-model="showPasswordDialog"
      @success="showPasswordDialog = false"
    />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Edit, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { authAPI } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import ChangePasswordDialog from '@/components/ChangePasswordDialog.vue'

const authStore = useAuthStore()
const formRef = ref()
const editing = ref(false)
const saving = ref(false)
const showPasswordDialog = ref(false)
const form = reactive({
  username: '',
  email: '',
  avatar_url: '',
  major: '',
  grade: ''
})
const stats = reactive({
  items_count: 0,
  transactions_count: 0
})
const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 32, message: '用户名长度为 2-32 个字符', trigger: 'blur' }
  ]
}

const loadProfile = async () => {
  const [{ data: profile }, { data: statsData }] = await Promise.all([
    authAPI.getUserProfile(),
    authAPI.getUserStats()
  ])
  Object.assign(form, profile)
  Object.assign(stats, statsData)
}

const saveProfile = async () => {
  try {
    await formRef.value.validate()
    saving.value = true
    const { data } = await authAPI.updateProfile({
      username: form.username,
      avatar_url: form.avatar_url,
      major: form.major,
      grade: form.grade
    })
    Object.assign(form, data.user)
    authStore.user = data.user
    await authStore.getCurrentUser()
    editing.value = false
    ElMessage.success('个人资料已更新')
  } catch (error) {
    if (error?.response) ElMessage.error(error.response.data?.message || '更新失败')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    await loadProfile()
  } catch (error) {
    ElMessage.error('个人资料加载失败')
  }
})
</script>

<style lang="scss" scoped>
.profile-page {
  display: grid;
  gap: 22px;
}

.profile-hero {
  padding: 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-radius: 8px;
  color: #fff;
  background: var(--ink);
}

.profile-identity {
  display: flex;
  align-items: center;
  gap: 22px;

  :deep(.el-avatar) {
    color: var(--ink);
    background: var(--lime);
    font-size: 32px;
    font-weight: 800;
  }

  h1 {
    margin: 7px 0 4px;
    font: 760 38px/1.1 var(--font-display);
    letter-spacing: -0.04em;
  }

  p {
    margin: 0;
    color: rgba(255, 255, 255, 0.6);
  }
}

.profile-label {
  color: var(--lime);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;

  article {
    padding: 22px;
    display: grid;
    gap: 8px;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--paper);
  }

  span,
  small {
    color: var(--muted);
    font-size: 12px;
  }

  strong {
    font: 800 32px/1 var(--font-display);
  }
}

.profile-grid {
  display: grid;
  grid-template-columns: 1fr 310px;
  gap: 18px;
}

.card-title {
  display: flex;
  justify-content: space-between;
  align-items: center;

  > div {
    display: grid;
    gap: 5px;
  }

  span {
    font-weight: 750;
  }

  small {
    color: var(--muted);
  }
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 18px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
}

.security-panel {
  padding: 28px;
  border-radius: 8px;
  color: #fff;
  background: var(--coral);

  > span {
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }

  h2 {
    margin: 30px 0 12px;
    font: 740 27px/1.2 var(--font-display);
  }

  p {
    margin: 0 0 24px;
    color: rgba(255, 255, 255, 0.74);
    line-height: 1.7;
  }
}

.security-icon {
  width: 52px;
  height: 52px;
  margin-bottom: 20px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.42);
  border-radius: 16px;
  font-size: 23px;
}

@media (max-width: 820px) {
  .profile-hero {
    padding: 28px;
    align-items: flex-start;
    flex-direction: column;
    gap: 24px;
  }

  .stat-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .profile-grid,
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>

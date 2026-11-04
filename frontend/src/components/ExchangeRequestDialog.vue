<template>
  <el-dialog
    v-model="visible"
    title="申请交换"
    width="600px"
    :before-close="handleClose"
  >
    <div class="exchange-request-form">
      <!-- 目标物品信息 -->
      <div class="target-item">
        <h4>目标物品</h4>
        <div class="item-card">
          <div class="item-image">
            <img
              :src="targetItem?.image_url || '/default-item.svg'"
              :alt="targetItem?.title"
              @error="handleImageError"
            />
          </div>
          <div class="item-info">
            <h5>{{ targetItem?.title }}</h5>
            <p v-if="targetItem?.description">{{ targetItem.description }}</p>
            <div class="item-meta">
              <el-tag size="small" type="info">{{ targetItem?.category }}</el-tag>
              <span class="owner">拥有者：{{ targetItem?.owner?.username }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 我的物品选择 -->
      <div class="my-items">
        <h4>选择用于交换的物品</h4>
        <div v-if="myItems.length > 0" class="items-grid">
          <div
            v-for="item in myItems"
            :key="item.id"
            class="item-option"
            :class="{ selected: selectedItemId === item.id }"
            @click="selectItem(item.id)"
          >
            <div class="item-image">
              <img
                :src="item.image_url || '/default-item.svg'"
                :alt="item.title"
                @error="handleImageError"
              />
            </div>
            <div class="item-content">
              <h6>{{ item.title }}</h6>
              <p v-if="item.description">{{ item.description }}</p>
              <el-tag size="small" type="info">{{ item.category }}</el-tag>
            </div>
            <div class="selection-indicator">
              <el-icon v-if="selectedItemId === item.id"><Check /></el-icon>
            </div>
          </div>
        </div>
        <div v-else class="no-items">
          <el-empty description="您还没有可交换的物品">
            <el-button type="primary" @click="goToPublish">发布物品</el-button>
          </el-empty>
        </div>
      </div>

      <!-- 交换说明 -->
      <div class="exchange-message">
        <h4>交换说明</h4>
        <el-input
          v-model="message"
          type="textarea"
          :rows="4"
          placeholder="请说明您的交换意向，比如为什么想要这个物品，您的物品有什么特点等..."
          maxlength="500"
          show-word-limit
        />
      </div>

      <!-- 联系方式 -->
      <div class="contact-info">
        <h4>联系方式</h4>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-input
              v-model="contactPhone"
              placeholder="手机号码"
              prefix-icon="Phone"
            />
          </el-col>
          <el-col :span="12">
            <el-input
              v-model="contactWechat"
              placeholder="微信号（可选）"
              prefix-icon="ChatDotRound"
            />
          </el-col>
        </el-row>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button
          type="primary"
          :loading="submitting"
          :disabled="!canSubmit"
          @click="submitRequest"
        >
          发送交换申请
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { itemsAPI } from '@/api/items'
import { transactionsAPI } from '@/api/transactions'
import { ElMessage } from 'element-plus'
import { Check } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  targetItem: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'success'])

const router = useRouter()
const authStore = useAuthStore()

// 响应式数据
const visible = ref(false)
const myItems = ref([])
const selectedItemId = ref(null)
const message = ref('')
const contactPhone = ref('')
const contactWechat = ref('')
const submitting = ref(false)
const loading = ref(false)

// 计算属性
const canSubmit = computed(() => {
  return selectedItemId.value && message.value.trim() && contactPhone.value.trim()
})

// 监听显示状态
watch(() => props.modelValue, (newVal) => {
  visible.value = newVal
  if (newVal) {
    loadMyItems()
    resetForm()
  }
})

watch(visible, (newVal) => {
  emit('update:modelValue', newVal)
})

// 获取我的物品
const loadMyItems = async () => {
  try {
    loading.value = true
    const response = await itemsAPI.getMyItems({
      status: 'available',
      page_size: 20
    })
    myItems.value = response.data.items
  } catch (error) {
    console.error('获取我的物品失败:', error)
    ElMessage.error('获取我的物品失败')
  } finally {
    loading.value = false
  }
}

// 选择物品
const selectItem = (itemId) => {
  selectedItemId.value = selectedItemId.value === itemId ? null : itemId
}

// 提交交换申请
const submitRequest = async () => {
  try {
    submitting.value = true

    await transactionsAPI.createExchangeRequest({
      target_item_id: props.targetItem.id,
      offered_item_id: selectedItemId.value,
      message: message.value,
      contact_phone: contactPhone.value,
      contact_wechat: contactWechat.value
    })

    ElMessage.success('交换申请已发送')
    emit('success')
    handleClose()
  } catch (error) {
    console.error('发送交换申请失败:', error)
    ElMessage.error(error.response?.data?.message || '发送交换申请失败')
  } finally {
    submitting.value = false
  }
}

// 重置表单
const resetForm = () => {
  selectedItemId.value = null
  message.value = ''
  contactPhone.value = authStore.user?.phone || ''
  contactWechat.value = ''
}

// 关闭对话框
const handleClose = () => {
  visible.value = false
}

// 跳转到发布页面
const goToPublish = () => {
  handleClose()
  router.push('/items?publish=1')
}

// 处理图片错误
const handleImageError = (e) => {
  e.target.src = '/default-item.svg'
}

// 初始化
onMounted(() => {
  if (authStore.user?.phone) {
    contactPhone.value = authStore.user.phone
  }
})
</script>

<style lang="scss" scoped>
@use "@/styles/variables.scss" as *;

.exchange-request-form {
  .target-item {
    margin-bottom: 24px;

    h4 {
      margin: 0 0 12px 0;
      font-size: 16px;
      font-weight: 600;
      color: $text-color-primary;
    }

    .item-card {
      display: flex;
      padding: 16px;
      border: 1px solid $border-color-light;
      border-radius: $border-radius-base;
      background: $bg-color-light;

      .item-image {
        width: 80px;
        height: 80px;
        border-radius: $border-radius-small;
        overflow: hidden;
        flex-shrink: 0;

        img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }
      }

      .item-info {
        flex: 1;
        margin-left: 12px;

        h5 {
          margin: 0 0 8px 0;
          font-size: 16px;
          font-weight: 500;
          color: $text-color-primary;
        }

        p {
          margin: 0 0 8px 0;
          font-size: 14px;
          color: $text-color-secondary;
          line-height: 1.4;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }

        .item-meta {
          display: flex;
          align-items: center;
          gap: 12px;

          .owner {
            font-size: 12px;
            color: $text-color-secondary;
          }
        }
      }
    }
  }

  .my-items {
    margin-bottom: 24px;

    h4 {
      margin: 0 0 12px 0;
      font-size: 16px;
      font-weight: 600;
      color: $text-color-primary;
    }

    .items-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 12px;
      max-height: 300px;
      overflow-y: auto;
    }

    .item-option {
      position: relative;
      border: 2px solid $border-color-light;
      border-radius: $border-radius-base;
      overflow: hidden;
      cursor: pointer;
      transition: all 0.3s ease;

      &:hover {
        border-color: $color-primary;
      }

      &.selected {
        border-color: $color-primary;
        background: rgba($color-primary, 0.05);
      }

      .item-image {
        height: 120px;
        overflow: hidden;

        img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }
      }

      .item-content {
        padding: 12px;

        h6 {
          margin: 0 0 4px 0;
          font-size: 14px;
          font-weight: 500;
          color: $text-color-primary;
          display: -webkit-box;
          -webkit-line-clamp: 1;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }

        p {
          margin: 0 0 8px 0;
          font-size: 12px;
          color: $text-color-secondary;
          line-height: 1.3;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
      }

      .selection-indicator {
        position: absolute;
        top: 8px;
        right: 8px;
        width: 24px;
        height: 24px;
        background: $color-primary;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 14px;
      }
    }

    .no-items {
      text-align: center;
      padding: 40px 20px;
    }
  }

  .exchange-message {
    margin-bottom: 24px;

    h4 {
      margin: 0 0 12px 0;
      font-size: 16px;
      font-weight: 600;
      color: $text-color-primary;
    }
  }

  .contact-info {
    h4 {
      margin: 0 0 12px 0;
      font-size: 16px;
      font-weight: 600;
      color: $text-color-primary;
    }
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

// 响应式设计
@media (max-width: 768px) {
  .exchange-request-form {
    .target-item .item-card {
      flex-direction: column;

      .item-image {
        width: 100%;
        height: 150px;
        margin-bottom: 12px;
      }

      .item-info {
        margin-left: 0;
      }
    }

    .my-items .items-grid {
      grid-template-columns: 1fr;
    }
  }
}
</style>

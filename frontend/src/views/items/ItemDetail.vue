<template>
  <div class="item-detail-page">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="8" animated />
    </div>

    <!-- 物品详情 -->
    <div v-else-if="item" class="item-detail">
      <!-- 返回按钮 -->
      <div class="back-button">
        <el-button @click="$router.back()">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
      </div>

      <!-- 物品信息 -->
      <el-row :gutter="24">
        <el-col :lg="12" :md="24">
          <!-- 物品图片 -->
          <div class="item-images">
            <div class="main-image">
              <img
                :src="currentImage || '/default-item.svg'"
                :alt="item.title"
                @error="handleImageError"
              />
            </div>
            <div v-if="item.images && item.images.length > 1" class="image-thumbnails">
              <div
                v-for="(image, index) in item.images"
                :key="index"
                class="thumbnail"
                :class="{ active: currentImage === image }"
                @click="currentImage = image"
              >
                <img :src="image" :alt="`图片${index + 1}`" @error="handleImageError" />
              </div>
            </div>
          </div>
        </el-col>

        <el-col :lg="12" :md="24">
          <!-- 物品基本信息 -->
          <div class="item-info">
            <div class="item-header">
              <h1 class="item-title">{{ item.title }}</h1>
              <div class="item-status">
                <el-tag
                  :type="getStatusType(item.status)"
                  size="large"
                >
                  {{ getStatusText(item.status) }}
                </el-tag>
              </div>
            </div>

            <div class="item-meta">
              <div class="meta-item">
                <span class="label">分类：</span>
                <el-tag type="info">{{ item.category }}</el-tag>
              </div>
              <div class="meta-item">
                <span class="label">状态：</span>
                <el-tag :type="getConditionType(item.condition)">
                  {{ getConditionText(item.condition) }}
                </el-tag>
              </div>
              <div class="meta-item">
                <span class="label">位置：</span>
                <span class="value">
                  <el-icon><Location /></el-icon>
                  {{ [item.location_campus, item.location_building].filter(Boolean).join(' · ') || '校内面交' }}
                </span>
              </div>
              <div class="meta-item">
                <span class="label">发布时间：</span>
                <span class="value">{{ formatDate(item.created_at) }}</span>
              </div>
            </div>

            <div class="item-description"><h3>交易方式</h3><p>{{ item.transaction_type }}<span v-if="item.sale_price"> · ¥{{ item.sale_price }}</span><span v-if="item.rental_price_day"> · ¥{{ item.rental_price_day }}/天</span></p></div>
            <div class="item-description">
              <h3>物品描述</h3>
              <p>{{ item.description || '卖家暂未填写商品描述' }}</p>
            </div>

            <!-- 物品拥有者信息 -->
            <div class="owner-info">
              <h3>物品拥有者</h3>
              <div class="owner-card">
                <el-avatar :size="50" :src="item.owner?.avatar_url">
                  {{ item.owner?.username?.charAt(0) }}
                </el-avatar>
                <div class="owner-details">
                  <div class="owner-name">{{ item.owner?.username }}</div>
                  <div class="owner-meta">
                    <span>加入时间：{{ formatDate(item.owner?.created_at) }}</span>
                  </div>
                </div>
                <div class="owner-actions">
                  <el-button
                    size="small"
                    @click="contactOwner"
                  >
                    <el-icon><ChatDotRound /></el-icon>
                    联系TA
                  </el-button>
                </div>
              </div>
            </div>

            <!-- 操作按钮 -->
            <div class="action-buttons">
              <template v-if="isOwner">
                <el-button
                  type="primary"
                  @click="editItem"
                >
                  <el-icon><Edit /></el-icon>
                  编辑物品
                </el-button>
                <el-button
                  type="danger"
                  @click="deleteItem"
                >
                  <el-icon><Delete /></el-icon>
                  删除物品
                </el-button>
              </template>
              <template v-else>
                <el-button
                  type="primary"
                  size="large"
                  :disabled="item.status !== 'available'"
                  v-if="item.transaction_type?.includes('交换')"
                  @click="requestExchange"
                >
                  <el-icon><Refresh /></el-icon>
                  申请交换
                </el-button>
                <el-button
                  size="large"
                  @click="contactOwner"
                >
                  <el-icon><ChatDotRound /></el-icon>
                  联系拥有者
                </el-button>
              </template>
            </div>
          </div>
        </el-col>
      </el-row>

      <!-- 相关物品推荐 -->
      <div class="related-items">
        <h3>相关物品推荐</h3>
        <div v-if="relatedItems.length > 0" class="related-grid">
          <div
            v-for="relatedItem in relatedItems"
            :key="relatedItem.id"
            class="related-item"
            @click="goToItem(relatedItem.id)"
          >
            <div class="related-image">
              <img
                :src="relatedItem.images?.[0] || '/default-item.svg'"
                :alt="relatedItem.title"
                @error="handleImageError"
              />
            </div>
            <div class="related-content">
              <h4 class="related-title">{{ relatedItem.title }}</h4>
              <p v-if="relatedItem.description" class="related-description">{{ relatedItem.description }}</p>
              <div class="related-meta">
                <el-tag size="small" type="info">{{ relatedItem.category }}</el-tag>
                <span class="related-time">{{ formatRelativeTime(relatedItem.created_at) }}</span>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="no-related">
          <el-empty description="暂无相关物品" />
        </div>
      </div>
    </div>

    <!-- 错误状态 -->
    <div v-else class="error-state">
      <el-result
        icon="error"
        title="物品不存在"
        sub-title="该物品可能已被删除或不存在"
      >
        <template #extra>
          <el-button type="primary" @click="$router.push('/items')">
            返回物品列表
          </el-button>
        </template>
      </el-result>
    </div>

    <!-- 交换申请对话框 -->
    <ExchangeRequestDialog
      v-model="showExchangeDialog"
      :target-item="item"
      @success="handleExchangeSuccess"
    />

    <!-- 编辑物品对话框 -->
    <EditItemDialog
      v-model="showEditDialog"
      :item="item"
      @success="handleEditSuccess"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { itemsAPI } from '@/api/items'
import { formatDate, formatRelativeTime } from '@/utils'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft,
  Location,
  ChatDotRound,
  Edit,
  Delete,
  Refresh
} from '@element-plus/icons-vue'
import ExchangeRequestDialog from '@/components/ExchangeRequestDialog.vue'
import EditItemDialog from '@/components/EditItemDialog.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

// 响应式数据
const loading = ref(false)
const item = ref(null)
const relatedItems = ref([])
const currentImage = ref('')
const showExchangeDialog = ref(false)
const showEditDialog = ref(false)

// 计算属性
const isOwner = computed(() => {
  return authStore.user && item.value && authStore.user.id === item.value.owner_id
})

// 获取物品详情
const getItemDetail = async () => {
  try {
    loading.value = true
    const response = await itemsAPI.getItemById(route.params.id)
    item.value = response.data.item || response.data

    // 设置默认图片
    if (item.value.images && item.value.images.length > 0) {
      currentImage.value = item.value.images[0]
    } else {
      currentImage.value = item.value.image_url || '/default-item.svg'
    }

    // 获取相关物品
    getRelatedItems()
  } catch (error) {
    console.error('获取物品详情失败:', error)
    ElMessage.error('获取物品详情失败')
  } finally {
    loading.value = false
  }
}

// 获取相关物品
const getRelatedItems = async () => {
  try {
    const response = await itemsAPI.getItems({
      category: item.value.category,
      per_page: 4,
      exclude: item.value.id
    })
    relatedItems.value = response.data.items
  } catch (error) {
    console.error('获取相关物品失败:', error)
  }
}

// 申请交换
const requestExchange = () => {
  if (!authStore.isLoggedIn) {
    ElMessage.warning('请先登录')
    router.push('/login')
    return
  }
  showExchangeDialog.value = true
}

// 联系拥有者
const contactOwner = () => {
  if (!authStore.isLoggedIn) {
    ElMessage.warning('请先登录')
    router.push('/login')
    return
  }
  // 跳转到消息页面
  router.push(`/messages?user=${item.value.owner_id}`)
}

// 编辑物品
const editItem = () => {
  showEditDialog.value = true
}

// 删除物品
const deleteItem = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要删除这个物品吗？删除后无法恢复。',
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await itemsAPI.deleteItem(item.value.id)
    ElMessage.success('物品删除成功')
    router.push('/items')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除物品失败:', error)
      ElMessage.error('删除物品失败')
    }
  }
}

// 跳转到其他物品
const goToItem = (id) => {
  router.push(`/items/${id}`)
}

// 交换成功
const handleExchangeSuccess = () => {
  showExchangeDialog.value = false
  ElMessage.success('交换申请已发送')
}

// 编辑成功
const handleEditSuccess = () => {
  showEditDialog.value = false
  getItemDetail()
}

// 获取状态类型
const getStatusType = (status) => {
  const types = {
    available: 'success',
    pending: 'warning',
    exchanged: 'info'
  }
  return types[status] || 'info'
}

// 获取状态文本
const getStatusText = (status) => {
  const texts = {
    available: '在架',
    pending: '交换中',
    exchanged: '已交换', sold: '已售出', rented_out: '租借中', unavailable: '已下架'
  }
  return texts[status] || '未知'
}

// 获取状态类型
const getConditionType = (condition) => {
  const types = {
    new: 'success',
    like_new: 'success',
    good: 'warning',
    fair: 'info'
  }
  return types[condition] || 'info'
}

// 获取状态文本
const getConditionText = (condition) => {
  const texts = {
    new: '全新',
    like_new: '几乎全新',
    good: '良好',
    fair: '一般'
  }
  return texts[condition] || condition || '未说明'
}

// 处理图片错误
const handleImageError = (e) => {
  // 防止无限循环，只有当前src不是默认图片时才设置
  if (e.target.src !== window.location.origin + '/default-item.svg') {
    e.target.src = '/default-item.svg'
  }
}

// 初始化
watch(() => route.params.id, () => { currentImage.value = ''; getItemDetail() })
onMounted(() => {
  getItemDetail()
})
</script>

<style lang="scss" scoped>
@use "@/styles/variables.scss" as *;

.item-detail-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.loading-container {
  padding: 40px;
}

.back-button {
  margin-bottom: 20px;
}

.item-detail {
  .item-images {
    .main-image {
      width: 100%;
      height: 400px;
      border-radius: $border-radius-base;
      overflow: hidden;
      margin-bottom: 16px;

      img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
    }

    .image-thumbnails {
      display: flex;
      gap: 8px;

      .thumbnail {
        width: 80px;
        height: 80px;
        border-radius: $border-radius-small;
        overflow: hidden;
        cursor: pointer;
        border: 2px solid transparent;
        transition: border-color 0.3s ease;

        &.active {
          border-color: $color-primary;
        }

        img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }
      }
    }
  }

  .item-info {
    .item-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 24px;

      .item-title {
        margin: 0;
        font-size: 28px;
        font-weight: 600;
        color: $text-color-primary;
        flex: 1;
        margin-right: 16px;
      }
    }

    .item-meta {
      margin-bottom: 24px;

      .meta-item {
        display: flex;
        align-items: center;
        margin-bottom: 12px;

        .label {
          font-weight: 500;
          color: $text-color-secondary;
          width: 80px;
          flex-shrink: 0;
        }

        .value {
          display: flex;
          align-items: center;
          gap: 4px;
          color: $text-color-primary;
        }
      }
    }

    .item-description {
      margin-bottom: 24px;

      h3 {
        margin: 0 0 12px 0;
        font-size: 18px;
        font-weight: 600;
        color: $text-color-primary;
      }

      p {
        margin: 0;
        line-height: 1.6;
        color: $text-color-primary;
        white-space: pre-wrap;
      }
    }

    .owner-info {
      margin-bottom: 24px;

      h3 {
        margin: 0 0 16px 0;
        font-size: 18px;
        font-weight: 600;
        color: $text-color-primary;
      }

      .owner-card {
        display: flex;
        align-items: center;
        padding: 16px;
        border: 1px solid $border-color-light;
        border-radius: $border-radius-base;
        background: $bg-color-light;

        .owner-details {
          flex: 1;
          margin-left: 12px;

          .owner-name {
            font-size: 16px;
            font-weight: 500;
            color: $text-color-primary;
            margin-bottom: 4px;
          }

          .owner-meta {
            font-size: 14px;
            color: $text-color-secondary;
          }
        }
      }
    }

    .action-buttons {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }
  }

  .related-items {
    margin-top: 48px;

    h3 {
      margin: 0 0 24px 0;
      font-size: 20px;
      font-weight: 600;
      color: $text-color-primary;
    }

    .related-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
      gap: 20px;
    }

    .related-item {
      border: 1px solid $border-color-light;
      border-radius: $border-radius-base;
      overflow: hidden;
      cursor: pointer;
      transition: all 0.3s ease;

      &:hover {
        transform: translateY(-2px);
        box-shadow: $box-shadow-light;
      }

      .related-image {
        height: 150px;
        overflow: hidden;

        img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }
      }

      .related-content {
        padding: 12px;

        .related-title {
          margin: 0 0 8px 0;
          font-size: 14px;
          font-weight: 500;
          color: $text-color-primary;
          display: -webkit-box;
          -webkit-line-clamp: 1;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }

        .related-description {
          margin: 0 0 8px 0;
          font-size: 12px;
          color: $text-color-secondary;
          line-height: 1.4;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }

        .related-meta {
          display: flex;
          justify-content: space-between;
          align-items: center;

          .related-time {
            font-size: 12px;
            color: $text-color-secondary;
          }
        }
      }
    }

    .no-related {
      text-align: center;
      padding: 40px 20px;
    }
  }
}

.error-state {
  padding: 40px 20px;
  text-align: center;
}

// 响应式设计
@media (max-width: 768px) {
  .item-detail-page {
    padding: 16px;
  }

  .item-detail {
    .item-info {
      .item-header {
        flex-direction: column;
        align-items: flex-start;

        .item-title {
          margin-right: 0;
          margin-bottom: 12px;
        }
      }

      .action-buttons {
        flex-direction: column;

        .el-button {
          width: 100%;
        }
      }
    }

    .related-grid {
      grid-template-columns: 1fr;
    }
  }
}
</style>

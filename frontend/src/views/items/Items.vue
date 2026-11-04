<template>
  <div class="items-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <h1 class="page-title">
            <el-icon><Box /></el-icon>
            {{ route.query.mine === '1' ? '我的闲置' : '校园闲置' }}
          </h1>
          <p class="page-description">分享闲置物品，寻找需要的物品</p>
        </div>
        <div class="header-right">
          <el-button
            type="primary"
            size="large"
            @click="requestPublish"
          >
            <el-icon><Plus /></el-icon>
            发布物品
          </el-button>
        </div>
      </div>
    </div>

    <!-- 搜索筛选 -->
    <div class="search-section">
      <el-card>
        <div class="search-form">
          <div class="search-row">
            <el-input
              v-model="searchForm.keyword"
              placeholder="搜索物品名称或描述"
              class="search-input"
              clearable
              @keyup.enter="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>

            <el-select
              v-model="searchForm.category"
              placeholder="选择分类"
              clearable
              class="category-select"
            >
              <el-option
                v-for="category in categories"
                :key="category"
                :label="category"
                :value="category"
              />
            </el-select>

            <el-select
              v-model="searchForm.condition"
              placeholder="物品状态"
              clearable
              class="condition-select"
            >
              <el-option label="全新" value="全新" />
              <el-option label="九成新" value="九成新" />
              <el-option label="八成新" value="八成新" />
              <el-option label="有使用痕迹" value="有使用痕迹" />
            </el-select>

            <el-button type="primary" @click="handleSearch">
              <el-icon><Search /></el-icon>
              搜索
            </el-button>
          </div>

          <div class="filter-row">
            <el-radio-group v-model="searchForm.sort" @change="handleSearch">
              <el-radio-button label="created_at">最新发布</el-radio-button>
              <el-radio-button label="updated_at">最近更新</el-radio-button>
              
            </el-radio-group>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 物品列表 -->
    <div class="items-section">
      <el-card>
        <template #header>
          <div class="section-header">
            <span>物品列表</span>
            <span class="item-count">共 {{ total }} 个物品</span>
          </div>
        </template>

        <!-- 加载状态 -->
        <div v-if="loading" class="loading-container">
          <el-skeleton :rows="6" animated />
        </div>

        <!-- 物品网格 -->
        <div v-else-if="items.length > 0" class="items-grid">
          <div
            v-for="item in items"
            :key="item.id"
            class="item-card"
            @click="goToDetail(item.id)"
          >
            <div class="item-image">
              <img
                :src="item.images?.[0] || '/default-item.svg'"
                :alt="item.title"
                @error="handleImageError"
              />
              <div class="item-status">
                <el-tag
                  :type="getStatusType(item.status)"
                  size="small"
                >
                  {{ getStatusText(item.status) }}
                </el-tag>
              </div>
            </div>

            <div class="item-content">
              <h3 class="item-title">{{ item.title }}</h3>
              <p v-if="item.description" class="item-description">{{ item.description }}</p>

              <div class="item-meta">
                <div class="meta-row">
                  <el-tag size="small" type="info">{{ item.category }}</el-tag>
                  <el-tag size="small" :type="getConditionType(item.condition)">
                    {{ getConditionText(item.condition) }}
                  </el-tag>
                </div>

                <div class="meta-row">
                  <span class="location">
                    <el-icon><Location /></el-icon>
                    {{ [item.location_campus, item.location_building].filter(Boolean).join(' · ') || '校内面交' }}
                  </span>
                  <span class="time">
                    {{ formatRelativeTime(item.created_at) }}
                  </span>
                </div>
              </div>

              <div class="item-footer">
                <div class="owner-info">
                  <el-avatar :size="24" :src="item.owner?.avatar_url">
                    {{ item.owner?.username?.charAt(0) }}
                  </el-avatar>
                  <span class="owner-name">{{ item.owner?.username }}</span>
                </div>

                <div class="item-actions">
                  <el-button
                    size="small"
                    type="primary"
                    plain
                    @click.stop="handleExchange(item)"
                  >
                    {{ item.transaction_type.includes('交换') ? '申请交换' : '查看详情' }}
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-else class="empty-state">
          <el-empty description="暂无物品">
            <el-button type="primary" @click="requestPublish">
              发布第一个物品
            </el-button>
          </el-empty>
        </div>

        <!-- 分页 -->
        <div v-if="total > pageSize" class="pagination-container">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :total="total"
            :page-sizes="[12, 24, 48]"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </el-card>
    </div>

    <!-- 创建物品对话框 -->
    <CreateItemDialog
      v-model="showCreateDialog"
      @success="handleCreateSuccess"
    />

    <!-- 申请交换对话框 -->
    <ExchangeRequestDialog
      v-model="showExchangeDialog"
      :target-item="selectedItem"
      @success="handleExchangeSuccess"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { itemsAPI } from '@/api/items'
import { formatRelativeTime } from '@/utils'
import { ElMessage } from 'element-plus'
import {
  Box,
  Plus,
  Search,
  Location
} from '@element-plus/icons-vue'
import CreateItemDialog from '@/components/CreateItemDialog.vue'
import ExchangeRequestDialog from '@/components/ExchangeRequestDialog.vue'

const router = useRouter()
const route = useRoute()
const requestPublish = () => {
  if (!authStore.isAuthenticated) { router.push('/login'); return }
  showCreateDialog.value = true
}
const authStore = useAuthStore()

// 响应式数据
const loading = ref(false)
const items = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(12)
const showCreateDialog = ref(false)
const showExchangeDialog = ref(false)
const selectedItem = ref(null)

// 搜索表单
const searchForm = reactive({
  keyword: route.query.search || '',
  category: route.query.category || '',
  condition: '',
  sort: 'created_at'
})

// 物品分类
const categories = [
  '电子产品', '书籍', '服装', '家居用品', '运动器材',
  '乐器', '工具', '玩具', '艺术品', '其他'
]

// 获取物品列表
const getItems = async () => {
  try {
    loading.value = true
    const params = {
      page: currentPage.value,
      per_page: pageSize.value,
      search: searchForm.keyword,
      category: searchForm.category,
      condition: searchForm.condition,
      sort_by: searchForm.sort
    }

    // 移除空值
    Object.keys(params).forEach(key => {
      if (params[key] === '' || params[key] === null || params[key] === undefined) {
        delete params[key]
      }
    })

    const response = route.query.mine === '1' && authStore.isAuthenticated
      ? await itemsAPI.getMyItems(params)
      : await itemsAPI.getItems(params)
    items.value = response.data.items
    total.value = response.data.meta?.total_items ?? response.data.total ?? 0
  } catch (error) {
    console.error('获取物品列表失败:', error)
    ElMessage.error('获取物品列表失败')
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  currentPage.value = 1
  getItems()
}

// 分页
const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
  getItems()
}

const handleCurrentChange = (page) => {
  currentPage.value = page
  getItems()
}

// 跳转详情
const goToDetail = (id) => {
  router.push(`/items/${id}`)
}

// 申请交换
const handleExchange = (item) => {
  if (!authStore.isAuthenticated) { router.push('/login'); return }
  if (!item.transaction_type.includes('交换')) {
    goToDetail(item.id)
    return
  }
  selectedItem.value = item
  showExchangeDialog.value = true
}

// 创建成功
const handleCreateSuccess = () => {
  showCreateDialog.value = false
  getItems()
}

// 交换成功
const handleExchangeSuccess = () => {
  showExchangeDialog.value = false
  ElMessage.success('交换申请已发送')
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
    exchanged: '已交换',
    sold: '已售出',
    rented_out: '租借中',
    unavailable: '已下架'
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
  return condition || '未说明'
}

// 处理图片错误
const handleImageError = (e) => {
  e.target.src = '/default-item.svg'
}

// 初始化
watch(() => route.query, () => {
  searchForm.keyword = route.query.search || ''
  searchForm.category = route.query.category || ''
  handleSearch()
  if (route.query.publish === '1') requestPublish()
})
onMounted(() => {
  getItems()
  if (route.query.publish === '1') requestPublish()
})
</script>

<style lang="scss" scoped>
@use "@/styles/variables.scss" as *;

.items-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;

  .header-content {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .header-left {
      .page-title {
        display: flex;
        align-items: center;
        gap: 8px;
        margin: 0 0 8px 0;
        font-size: 28px;
        font-weight: 600;
        color: $text-color-primary;
      }

      .page-description {
        margin: 0;
        color: $text-color-secondary;
        font-size: 16px;
      }
    }
  }
}

.search-section {
  margin-bottom: 24px;

  .search-form {
    .search-row {
      display: flex;
      gap: 16px;
      margin-bottom: 16px;

      .search-input {
        flex: 1;
        max-width: 400px;
      }

      .category-select,
      .condition-select {
        width: 150px;
      }
    }

    .filter-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
  }
}

.items-section {
  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .item-count {
      color: $text-color-secondary;
      font-size: 14px;
    }
  }

  .loading-container {
    padding: 20px;
  }

  .items-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 20px;
    margin-top: 20px;
  }

  .item-card {
    border: 1px solid $border-color-light;
    border-radius: $border-radius-base;
    overflow: hidden;
    transition: all 0.3s ease;
    cursor: pointer;
    background: white;

    &:hover {
      transform: translateY(-2px);
      box-shadow: $box-shadow-light;
      border-color: $color-primary;
    }

    .item-image {
      position: relative;
      height: 180px;
      overflow: hidden;

      img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        transition: transform 0.3s ease;
      }

      &:hover img {
        transform: scale(1.05);
      }

      .item-status {
        position: absolute;
        top: 8px;
        right: 8px;
      }
    }

    .item-content {
      padding: 16px;

      .item-title {
        margin: 0 0 8px 0;
        font-size: 16px;
        font-weight: 600;
        color: $text-color-primary;
        display: -webkit-box;
        -webkit-line-clamp: 1;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }

      .item-description {
        margin: 0 0 12px 0;
        color: $text-color-secondary;
        font-size: 14px;
        line-height: 1.4;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }

      .item-meta {
        margin-bottom: 12px;

        .meta-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;

          &:last-child {
            margin-bottom: 0;
          }

          .location {
            display: flex;
            align-items: center;
            gap: 4px;
            color: $text-color-secondary;
            font-size: 12px;
          }

          .time {
            color: $text-color-secondary;
            font-size: 12px;
          }
        }
      }

      .item-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;

        .owner-info {
          display: flex;
          align-items: center;
          gap: 8px;

          .owner-name {
            font-size: 14px;
            color: $text-color-secondary;
          }
        }
      }
    }
  }

  .empty-state {
    padding: 40px 20px;
    text-align: center;
  }

  .pagination-container {
    display: flex;
    justify-content: center;
    margin-top: 24px;
    padding-top: 24px;
    border-top: 1px solid $border-color-lighter;
  }
}

// 响应式设计
@media (max-width: 768px) {
  .items-page {
    padding: 16px;
  }

  .page-header .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .search-form .search-row {
    flex-direction: column;

    .search-input {
      max-width: none;
    }
  }

  .items-grid {
    grid-template-columns: 1fr;
  }
}
</style>

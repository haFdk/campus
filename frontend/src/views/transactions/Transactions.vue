<template>
  <div class="transactions-page">
    <div class="page-header">
      <h1>交易记录</h1>
      <p>查看您的所有交易历史记录</p>
    </div>

    <!-- 筛选器 -->
    <el-card class="filter-card">
      <el-form :model="filters" inline>
        <el-form-item label="交易类型">
          <el-select v-model="filters.type" placeholder="全部类型" clearable>
            <el-option label="闲置交易" value="item" />
          </el-select>
        </el-form-item>

        <el-form-item label="交易状态">
          <el-select v-model="filters.status" placeholder="全部状态" clearable>
            <el-option label="进行中" value="ongoing" />
            <el-option label="已完成" value="completed" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>

        <el-form-item label="角色">
          <el-select v-model="filters.role" placeholder="全部角色" clearable>
            <el-option label="发起者" value="initiator" />
            <el-option label="接受者" value="acceptor" />
          </el-select>
        </el-form-item>

        <el-form-item label="时间范围">
          <el-date-picker
            v-model="filters.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="searchTransactions">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="resetFilters">
            <el-icon><Refresh /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 交易列表 -->
    <el-card class="transactions-card">
      <div v-loading="loading" class="transactions-content">
        <div v-if="transactions.length === 0 && !loading" class="empty-state">
          <el-empty description="暂无交易记录">
            <el-button type="primary" @click="$router.push('/home')">
              去首页看看
            </el-button>
          </el-empty>
        </div>

        <div v-else class="transaction-list">
          <div
            v-for="transaction in transactions"
            :key="transaction.id"
            class="transaction-item"
            @click="viewTransactionDetail(transaction)"
          >
            <div class="transaction-header">
              <div class="transaction-info">
                <h3>{{ transaction.title }}</h3>
                <div class="transaction-meta">
                  <el-tag :type="getTypeTagType(transaction.type)" size="small">
                    {{ getTypeText(transaction.type) }}
                  </el-tag>
                  <el-tag :type="getStatusTagType(transaction.status)" size="small">
                    {{ getStatusText(transaction.status) }}
                  </el-tag>
                  <el-tag :type="getRoleTagType(transaction.role)" size="small">
                    {{ getRoleText(transaction.role) }}
                  </el-tag>
                </div>
              </div>
              <div class="transaction-amount">
                <span v-if="transaction.amount" class="amount">
                  ¥{{ transaction.amount }}
                </span>
                <span class="date">{{ formatDate(transaction.created_at) }}</span>
              </div>
            </div>

            <div class="transaction-content">
              <div class="participants">
                <div class="participant">
                  <el-avatar :size="40" :src="transaction.initiator.avatar_url">
                    {{ transaction.initiator.username?.charAt(0) }}
                  </el-avatar>
                  <div class="participant-info">
                    <div class="name">{{ transaction.initiator.username }}</div>
                    <div class="role">发起者</div>
                  </div>
                </div>

                <div class="exchange-icon">
                  <el-icon><Switch /></el-icon>
                </div>

                <div class="participant">
                  <el-avatar :size="40" :src="transaction.acceptor.avatar_url">
                    {{ transaction.acceptor.username?.charAt(0) }}
                  </el-avatar>
                  <div class="participant-info">
                    <div class="name">{{ transaction.acceptor.username }}</div>
                    <div class="role">接受者</div>
                  </div>
                </div>
              </div>

              <div class="transaction-description">
                {{ transaction.description }}
              </div>

              <div class="transaction-actions">
                <el-button
                  v-if="['accepted', 'in_progress'].includes(transaction.status)"
                  type="primary"
                  size="small"
                  @click.stop="completeTransaction(transaction)"
                >
                  标记完成
                </el-button>
                <el-button
                  v-if="transaction.status === 'completed' && !transaction.reviewed"
                  type="success"
                  size="small"
                  @click.stop="reviewTransaction(transaction)"
                >
                  评价
                </el-button>
                <el-button
                  size="small"
                  @click.stop="contactUser(transaction)"
                >
                  联系对方
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="total > 0" class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 交易详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="交易详情"
      width="600px"
    >
      <div v-if="selectedTransaction" class="transaction-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="交易编号">
            {{ selectedTransaction.id }}
          </el-descriptions-item>
          <el-descriptions-item label="交易类型">
            <el-tag :type="getTypeTagType(selectedTransaction.type)">
              {{ getTypeText(selectedTransaction.type) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="交易状态">
            <el-tag :type="getStatusTagType(selectedTransaction.status)">
              {{ getStatusText(selectedTransaction.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatDate(selectedTransaction.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="完成时间" v-if="selectedTransaction.completed_at">
            {{ formatDate(selectedTransaction.completed_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="交易金额" v-if="selectedTransaction.amount">
            ¥{{ selectedTransaction.amount }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="detail-section">
          <h4>交易描述</h4>
          <p>{{ selectedTransaction.description }}</p>
        </div>

        <div v-if="selectedTransaction.notes" class="detail-section">
          <h4>备注信息</h4>
          <p>{{ selectedTransaction.notes }}</p>
        </div>
      </div>
    </el-dialog>

    <ReviewDialog
      v-model="reviewDialogVisible"
      :transaction="selectedTransaction"
      @success="handleReviewSuccess"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Switch } from '@element-plus/icons-vue'
import { getTransactions, completeTransaction as completeTransactionApi } from '@/api/transactions'
import { formatDate } from '@/utils'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import ReviewDialog from '@/components/ReviewDialog.vue'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const transactions = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const detailDialogVisible = ref(false)
const selectedTransaction = ref(null)
const reviewDialogVisible = ref(false)

const filters = reactive({
  type: '',
  status: '',
  role: '',
  dateRange: null
})

onMounted(() => {
  fetchTransactions()
})

const fetchTransactions = async () => {
  try {
    loading.value = true
    const params = {
      page: currentPage.value,
      per_page: pageSize.value,
      ...filters
    }

    if (filters.dateRange) {
      params.start_date = filters.dateRange[0]
      params.end_date = filters.dateRange[1]
    }

    const response = await getTransactions(params)
    transactions.value = response.data.transactions
    total.value = response.data.total
  } catch (error) {
    console.error('获取交易记录失败:', error)
    ElMessage.error('获取交易记录失败')
  } finally {
    loading.value = false
  }
}

const searchTransactions = () => {
  currentPage.value = 1
  fetchTransactions()
}

const resetFilters = () => {
  Object.assign(filters, {
    type: '',
    status: '',
    role: '',
    dateRange: null
  })
  searchTransactions()
}

const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
  fetchTransactions()
}

const handleCurrentChange = (page) => {
  currentPage.value = page
  fetchTransactions()
}

const viewTransactionDetail = (transaction) => {
  selectedTransaction.value = transaction
  detailDialogVisible.value = true
}

const completeTransaction = async (transaction) => {
  try {
    await ElMessageBox.confirm(
      '确认标记此交易为已完成？',
      '确认操作',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await completeTransactionApi(transaction.id)
    ElMessage.success('交易已标记为完成')
    fetchTransactions()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('完成交易失败:', error)
      ElMessage.error('操作失败，请重试')
    }
  }
}

const reviewTransaction = (transaction) => {
  selectedTransaction.value = transaction
  reviewDialogVisible.value = true
}

const contactUser = (transaction) => {
  const otherUserId = transaction.requester_id === authStore.user?.id
    ? transaction.provider_id
    : transaction.requester_id
  router.push(`/messages?user=${otherUserId}`)
}

const handleReviewSuccess = () => {
  reviewDialogVisible.value = false
  fetchTransactions()
}

const getTypeText = (type) => {
  const typeMap = {
    item: '闲置交易',
  }
  return typeMap[type] || type
}

const getTypeTagType = (type) => {
  const typeMap = {
    item: 'success',
  }
  return typeMap[type] || ''
}

const getStatusText = (status) => {
  const statusMap = {
    pending_approval: '待确认',
    accepted: '已接受',
    in_progress: '进行中',
    completed: '已完成',
    rejected: '已拒绝',
    cancelled_by_requester: '已取消',
    cancelled_by_provider: '已取消'
  }
  return statusMap[status] || status
}

const getStatusTagType = (status) => {
  const statusMap = {
    pending_approval: 'warning',
    accepted: 'primary',
    in_progress: 'warning',
    completed: 'success',
    rejected: 'danger',
    cancelled_by_requester: 'info',
    cancelled_by_provider: 'info'
  }
  return statusMap[status] || ''
}

const getRoleText = (role) => {
  const roleMap = {
    initiator: '发起者',
    acceptor: '接受者'
  }
  return roleMap[role] || role
}

const getRoleTagType = (role) => {
  const roleMap = {
    initiator: 'primary',
    acceptor: 'success'
  }
  return roleMap[role] || ''
}
</script>

<style lang="scss" scoped>
.transactions-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 20px;

  h1 {
    margin: 0 0 8px 0;
    color: #303133;
    font-size: 24px;
    font-weight: 600;
  }

  p {
    margin: 0;
    color: #606266;
    font-size: 14px;
  }
}

.filter-card {
  margin-bottom: 20px;
}

.transactions-card {
  .transactions-content {
    min-height: 400px;
  }
}

.transaction-list {
  .transaction-item {
    border: 1px solid #ebeef5;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 16px;
    cursor: pointer;
    transition: all 0.3s;

    &:hover {
      border-color: #171717;
      box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
    }

    &:last-child {
      margin-bottom: 0;
    }
  }
}

.transaction-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;

  .transaction-info {
    flex: 1;

    h3 {
      margin: 0 0 8px 0;
      color: #303133;
      font-size: 16px;
      font-weight: 600;
    }

    .transaction-meta {
      display: flex;
      gap: 8px;
    }
  }

  .transaction-amount {
    text-align: right;

    .amount {
      display: block;
      color: #f56c6c;
      font-size: 18px;
      font-weight: 600;
      margin-bottom: 4px;
    }

    .date {
      color: #909399;
      font-size: 12px;
    }
  }
}

.transaction-content {
  .participants {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;

    .participant {
      display: flex;
      align-items: center;
      gap: 12px;

      .participant-info {
        .name {
          color: #303133;
          font-weight: 500;
          margin-bottom: 2px;
        }

        .role {
          color: #909399;
          font-size: 12px;
        }
      }
    }

    .exchange-icon {
      color: #171717;
      font-size: 20px;
    }
  }

  .transaction-description {
    color: #606266;
    font-size: 14px;
    line-height: 1.6;
    margin-bottom: 16px;
    padding: 12px;
    background-color: #f5f7fa;
    border-radius: 4px;
  }

  .transaction-actions {
    display: flex;
    gap: 8px;
  }
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.empty-state {
  padding: 60px 0;
}

.transaction-detail {
  .detail-section {
    margin-top: 20px;

    h4 {
      margin: 0 0 8px 0;
      color: #303133;
      font-size: 14px;
      font-weight: 600;
    }

    p {
      margin: 0;
      color: #606266;
      line-height: 1.6;
    }
  }
}

@media (max-width: 768px) {
  .transactions-page {
    padding: 10px;
  }

  .transaction-header {
    flex-direction: column;
    gap: 12px;

    .transaction-amount {
      text-align: left;
    }
  }

  .participants {
    flex-direction: column;
    gap: 12px;

    .exchange-icon {
      transform: rotate(90deg);
    }
  }
}
</style>

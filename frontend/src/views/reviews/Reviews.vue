<template>
  <div class="reviews-page">
    <div class="page-header">
      <h1>评价管理</h1>
      <p>管理您的评价记录，查看收到的评价和发出的评价</p>
    </div>

    <!-- 标签页 -->
    <el-tabs v-model="activeTab" @tab-change="handleTabChange">
      <el-tab-pane label="收到的评价" name="received">
        <div v-loading="loading" class="reviews-content">
          <div v-if="receivedReviews.length === 0 && !loading" class="empty-state">
            <el-empty description="暂无收到的评价">
              <el-button type="primary" @click="$router.push('/home')">
                去首页看看
              </el-button>
            </el-empty>
          </div>

          <div v-else class="review-list">
            <div
              v-for="review in receivedReviews"
              :key="review.id"
              class="review-item"
            >
              <div class="review-header">
                <div class="reviewer-info">
                  <el-avatar :size="50" :src="review.reviewer.avatar_url">
                    {{ review.reviewer.username?.charAt(0) }}
                  </el-avatar>
                  <div class="reviewer-details">
                    <h4>{{ review.reviewer.username }}</h4>
                    <div class="review-meta">
                      <el-rate
                        v-model="review.rating"
                        disabled
                        show-score
                        text-color="#ff9900"
                        score-template="{value} 分"
                      />
                      <span class="review-date">{{ formatDate(review.created_at) }}</span>
                    </div>
                  </div>
                </div>
                <div class="review-type">
                  <el-tag :type="getTypeTagType(review.transaction_type)" size="small">
                    {{ getTypeText(review.transaction_type) }}
                  </el-tag>
                </div>
              </div>

              <div class="review-content">
                <div class="review-text">
                  {{ review.content }}
                </div>

                <div v-if="review.transaction_title" class="transaction-info">
                  <span class="label">相关交易：</span>
                  <span class="value">{{ review.transaction_title }}</span>
                </div>

                <div class="review-actions">
                  <el-button
                    v-if="!review.replied"
                    type="primary"
                    size="small"
                    @click="replyToReview(review)"
                  >
                    回复评价
                  </el-button>
                  <el-button
                    size="small"
                    @click="contactReviewer(review)"
                  >
                    联系评价者
                  </el-button>
                </div>

                <div v-if="review.reply" class="review-reply">
                  <div class="reply-header">
                    <span class="reply-label">您的回复：</span>
                    <span class="reply-date">{{ formatDate(review.reply.created_at) }}</span>
                  </div>
                  <div class="reply-content">{{ review.reply.content }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="发出的评价" name="given">
        <div v-loading="loading" class="reviews-content">
          <div v-if="givenReviews.length === 0 && !loading" class="empty-state">
            <el-empty description="暂无发出的评价">
              <el-button type="primary" @click="$router.push('/transactions')">
                去交易记录看看
              </el-button>
            </el-empty>
          </div>

          <div v-else class="review-list">
            <div
              v-for="review in givenReviews"
              :key="review.id"
              class="review-item"
            >
              <div class="review-header">
                <div class="reviewer-info">
                  <el-avatar :size="50" :src="review.reviewee.avatar_url">
                    {{ review.reviewee.username?.charAt(0) }}
                  </el-avatar>
                  <div class="reviewer-details">
                    <h4>{{ review.reviewee.username }}</h4>
                    <div class="review-meta">
                      <el-rate
                        v-model="review.rating"
                        disabled
                        show-score
                        text-color="#ff9900"
                        score-template="{value} 分"
                      />
                      <span class="review-date">{{ formatDate(review.created_at) }}</span>
                    </div>
                  </div>
                </div>
                <div class="review-type">
                  <el-tag :type="getTypeTagType(review.transaction_type)" size="small">
                    {{ getTypeText(review.transaction_type) }}
                  </el-tag>
                </div>
              </div>

              <div class="review-content">
                <div class="review-text">
                  {{ review.content }}
                </div>

                <div v-if="review.transaction_title" class="transaction-info">
                  <span class="label">相关交易：</span>
                  <span class="value">{{ review.transaction_title }}</span>
                </div>

                <div class="review-actions">
                  <el-button
                    type="primary"
                    size="small"
                    @click="editReview(review)"
                  >
                    编辑评价
                  </el-button>
                  <el-button
                    type="danger"
                    size="small"
                    @click="deleteReview(review)"
                  >
                    删除评价
                  </el-button>
                </div>

                <div v-if="review.reply" class="review-reply">
                  <div class="reply-header">
                    <span class="reply-label">对方回复：</span>
                    <span class="reply-date">{{ formatDate(review.reply.created_at) }}</span>
                  </div>
                  <div class="reply-content">{{ review.reply.content }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

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

    <!-- 回复评价对话框 -->
    <el-dialog
      v-model="replyDialogVisible"
      title="回复评价"
      width="500px"
    >
      <div v-if="selectedReview" class="reply-dialog-content">
        <div class="original-review">
          <h4>原评价内容：</h4>
          <div class="review-info">
            <el-rate
              v-model="selectedReview.rating"
              disabled
              show-score
              text-color="#ff9900"
              score-template="{value} 分"
            />
            <p>{{ selectedReview.content }}</p>
          </div>
        </div>

        <el-form ref="replyFormRef" :model="replyForm" :rules="replyRules">
          <el-form-item label="回复内容" prop="content">
            <el-input
              v-model="replyForm.content"
              type="textarea"
              :rows="4"
              placeholder="请输入您的回复内容"
              maxlength="500"
              show-word-limit
            />
          </el-form-item>
        </el-form>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="replyDialogVisible = false">取消</el-button>
          <el-button
            type="primary"
            :loading="replyLoading"
            @click="submitReply"
          >
            发送回复
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 编辑评价对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑评价"
      width="500px"
    >
      <el-form ref="editFormRef" :model="editForm" :rules="editRules">
        <el-form-item label="评分" prop="rating">
          <el-rate
            v-model="editForm.rating"
            show-score
            text-color="#ff9900"
            score-template="{value} 分"
          />
        </el-form-item>

        <el-form-item label="评价内容" prop="content">
          <el-input
            v-model="editForm.content"
            type="textarea"
            :rows="4"
            placeholder="请输入评价内容"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button
            type="primary"
            :loading="editLoading"
            @click="submitEdit"
          >
            保存修改
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getReceivedReviews, getGivenReviews, replyToReview as replyToReviewApi, updateReview, deleteReview as deleteReviewApi } from '@/api/reviews'
import { formatDate } from '@/utils'
import { useRouter } from 'vue-router'

const router = useRouter()
const activeTab = ref('received')
const loading = ref(false)
const receivedReviews = ref([])
const givenReviews = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)

const replyDialogVisible = ref(false)
const editDialogVisible = ref(false)
const selectedReview = ref(null)
const replyLoading = ref(false)
const editLoading = ref(false)
const replyFormRef = ref()
const editFormRef = ref()

const replyForm = reactive({
  content: ''
})

const editForm = reactive({
  rating: 5,
  content: ''
})

const replyRules = {
  content: [
    { required: true, message: '请输入回复内容', trigger: 'blur' },
    { min: 5, max: 500, message: '回复内容长度在 5 到 500 个字符', trigger: 'blur' }
  ]
}

const editRules = {
  rating: [
    { required: true, message: '请选择评分', trigger: 'change' }
  ],
  content: [
    { required: true, message: '请输入评价内容', trigger: 'blur' },
    { min: 5, max: 500, message: '评价内容长度在 5 到 500 个字符', trigger: 'blur' }
  ]
}

const currentReviews = computed(() => {
  return activeTab.value === 'received' ? receivedReviews.value : givenReviews.value
})

onMounted(() => {
  fetchReviews()
})

const fetchReviews = async () => {
  try {
    loading.value = true
    const params = {
      page: currentPage.value,
      per_page: pageSize.value
    }

    if (activeTab.value === 'received') {
      const response = await getReceivedReviews(params)
      receivedReviews.value = response.data.reviews
      total.value = response.data.total
    } else {
      const response = await getGivenReviews(params)
      givenReviews.value = response.data.reviews
      total.value = response.data.total
    }
  } catch (error) {
    console.error('获取评价失败:', error)
    ElMessage.error('获取评价失败')
  } finally {
    loading.value = false
  }
}

const handleTabChange = (tab) => {
  activeTab.value = tab
  currentPage.value = 1
  fetchReviews()
}

const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
  fetchReviews()
}

const handleCurrentChange = (page) => {
  currentPage.value = page
  fetchReviews()
}

const replyToReview = (review) => {
  selectedReview.value = review
  replyForm.content = ''
  replyDialogVisible.value = true
}

const submitReply = async () => {
  if (!replyFormRef.value) return

  try {
    await replyFormRef.value.validate()
    replyLoading.value = true

    await replyToReviewApi(selectedReview.value.id, {
      content: replyForm.content
    })

    ElMessage.success('回复发送成功')
    replyDialogVisible.value = false
    fetchReviews()
  } catch (error) {
    console.error('回复失败:', error)
    ElMessage.error(error.message || '回复失败，请重试')
  } finally {
    replyLoading.value = false
  }
}

const editReview = (review) => {
  selectedReview.value = review
  editForm.rating = review.rating
  editForm.content = review.content
  editDialogVisible.value = true
}

const submitEdit = async () => {
  if (!editFormRef.value) return

  try {
    await editFormRef.value.validate()
    editLoading.value = true

    await updateReview(selectedReview.value.id, {
      rating: editForm.rating,
      content: editForm.content
    })

    ElMessage.success('评价修改成功')
    editDialogVisible.value = false
    fetchReviews()
  } catch (error) {
    console.error('修改评价失败:', error)
    ElMessage.error(error.message || '修改失败，请重试')
  } finally {
    editLoading.value = false
  }
}

const deleteReview = async (review) => {
  try {
    await ElMessageBox.confirm(
      '确认删除此评价？删除后无法恢复。',
      '确认删除',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await deleteReviewApi(review.id)
    ElMessage.success('评价删除成功')
    fetchReviews()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除评价失败:', error)
      ElMessage.error('删除失败，请重试')
    }
  }
}

const contactReviewer = (review) => {
  router.push(`/messages?user=${review.reviewer_id}`)
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
</script>

<style lang="scss" scoped>
.reviews-page {
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

.reviews-content {
  min-height: 400px;
}

.review-list {
  .review-item {
    border: 1px solid #ebeef5;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 16px;
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

.review-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;

  .reviewer-info {
    display: flex;
    align-items: center;
    gap: 12px;

    .reviewer-details {
      h4 {
        margin: 0 0 8px 0;
        color: #303133;
        font-size: 16px;
        font-weight: 600;
      }

      .review-meta {
        display: flex;
        align-items: center;
        gap: 12px;

        .review-date {
          color: #909399;
          font-size: 12px;
        }
      }
    }
  }
}

.review-content {
  .review-text {
    color: #606266;
    font-size: 14px;
    line-height: 1.6;
    margin-bottom: 12px;
    padding: 12px;
    background-color: #f5f7fa;
    border-radius: 4px;
  }

  .transaction-info {
    margin-bottom: 12px;
    font-size: 14px;

    .label {
      color: #909399;
    }

    .value {
      color: #303133;
      font-weight: 500;
    }
  }

  .review-actions {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
  }

  .review-reply {
    border-left: 3px solid #171717;
    padding-left: 12px;
    background-color: #fff9df;
    border-radius: 4px;
    padding: 12px;

    .reply-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;

      .reply-label {
        color: #171717;
        font-weight: 500;
        font-size: 12px;
      }

      .reply-date {
        color: #909399;
        font-size: 12px;
      }
    }

    .reply-content {
      color: #606266;
      font-size: 14px;
      line-height: 1.6;
    }
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

.reply-dialog-content {
  .original-review {
    margin-bottom: 20px;
    padding: 16px;
    background-color: #f5f7fa;
    border-radius: 4px;

    h4 {
      margin: 0 0 12px 0;
      color: #303133;
      font-size: 14px;
      font-weight: 600;
    }

    .review-info {
      p {
        margin: 8px 0 0 0;
        color: #606266;
        line-height: 1.6;
      }
    }
  }
}

.dialog-footer {
  text-align: right;

  .el-button {
    margin-left: 10px;
  }
}

@media (max-width: 768px) {
  .reviews-page {
    padding: 10px;
  }

  .review-header {
    flex-direction: column;
    gap: 12px;
  }

  .reviewer-info {
    width: 100%;
  }

  .review-actions {
    flex-wrap: wrap;
  }
}
</style>

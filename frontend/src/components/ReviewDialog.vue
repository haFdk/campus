<template>
  <el-dialog
    v-model="visible"
    title="评价服务"
    width="500px"
    :before-close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="100px"
      label-position="left"
    >
      <el-form-item label="服务信息">
        <div class="service-info">
          <h4>{{ transaction.title || '服务交易' }}</h4>
          <p class="service-type">{{ getServiceTypeLabel(transaction.type) }}</p>
          <div class="service-meta">
            <span class="provider">评价对象：{{ targetUser?.username }}</span>
            <span class="date">交易时间：{{ formatDate(transaction.created_at) }}</span>
          </div>
        </div>
      </el-form-item>

      <el-form-item label="评分" prop="rating">
        <el-rate
          v-model="form.rating"
          :max="5"
          show-text
          :texts="['很差', '较差', '一般', '满意', '非常满意']"
          size="large"
        />
      </el-form-item>

      <el-form-item label="评价内容" prop="content">
        <el-input
          v-model="form.content"
          type="textarea"
          :rows="4"
          placeholder="请详细描述您对此次服务的评价，包括服务质量、态度、专业程度等"
          maxlength="500"
          show-word-limit
        />
      </el-form-item>

      <el-form-item label="评价标签">
        <div class="tag-section">
          <div class="predefined-tags">
            <el-tag
              v-for="tag in predefinedTags"
              :key="tag"
              :type="form.tags.includes(tag) ? 'primary' : 'info'"
              :effect="form.tags.includes(tag) ? 'dark' : 'plain'"
              style="margin-right: 8px; margin-bottom: 8px; cursor: pointer"
              @click="toggleTag(tag)"
            >
              {{ tag }}
            </el-tag>
          </div>
          <div class="custom-tags">
            <el-tag
              v-for="tag in customTags"
              :key="tag"
              closable
              @close="removeCustomTag(tag)"
              style="margin-right: 8px; margin-bottom: 8px"
            >
              {{ tag }}
            </el-tag>
            <el-input
              v-if="inputVisible"
              ref="inputRef"
              v-model="inputValue"
              size="small"
              style="width: 100px"
              @keyup.enter="handleInputConfirm"
              @blur="handleInputConfirm"
            />
            <el-button
              v-else
              size="small"
              @click="showInput"
            >
              + 自定义标签
            </el-button>
          </div>
        </div>
      </el-form-item>

      <el-form-item label="是否推荐">
        <el-switch
          v-model="form.recommend"
          active-text="推荐"
          inactive-text="不推荐"
        />
      </el-form-item>

      <el-form-item label="改进建议">
        <el-input
          v-model="form.suggestions"
          type="textarea"
          :rows="2"
          placeholder="如有改进建议，请在此填写（可选）"
          maxlength="200"
          show-word-limit
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button
          type="primary"
          :loading="loading"
          @click="handleSubmit"
        >
          提交评价
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, watch, nextTick, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { submitReview } from '@/api/reviews'
import { useAuthStore } from '@/stores/auth'
import dayjs from 'dayjs'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  transaction: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['update:modelValue', 'success'])
const authStore = useAuthStore()

const visible = ref(false)
const loading = ref(false)
const formRef = ref()
const inputRef = ref()
const inputVisible = ref(false)
const inputValue = ref('')
const targetUser = computed(() => {
  if (props.transaction.requester_id === authStore.user?.id) {
    return props.transaction.provider
  }
  return props.transaction.requester
})

const form = reactive({
  rating: 5,
  content: '',
  tags: [],
  recommend: true,
  suggestions: ''
})

const predefinedTags = [
  '专业', '耐心', '准时', '友好', '高效',
  '认真', '负责', '沟通好', '描述真实', '价格合理'
]

const customTags = computed(() => {
  return form.tags.filter(tag => !predefinedTags.includes(tag))
})

const rules = {
  rating: [
    { required: true, message: '请选择评分', trigger: 'change' }
  ],
  content: [
    { required: true, message: '请输入评价内容', trigger: 'blur' },
    { min: 10, max: 500, message: '评价内容长度在 10 到 500 个字符', trigger: 'blur' }
  ]
}

watch(() => props.modelValue, (val) => {
  visible.value = val
})

watch(visible, (val) => {
  emit('update:modelValue', val)
})

const getServiceTypeLabel = (type) => {
  const typeMap = {
    item: '闲置交易',
  }
  return typeMap[type] || type
}

const formatDate = (date) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

const toggleTag = (tag) => {
  const index = form.tags.indexOf(tag)
  if (index > -1) {
    form.tags.splice(index, 1)
  } else {
    form.tags.push(tag)
  }
}

const removeCustomTag = (tag) => {
  const index = form.tags.indexOf(tag)
  if (index > -1) {
    form.tags.splice(index, 1)
  }
}

const showInput = () => {
  inputVisible.value = true
  nextTick(() => {
    inputRef.value?.focus()
  })
}

const handleInputConfirm = () => {
  if (inputValue.value && !form.tags.includes(inputValue.value)) {
    form.tags.push(inputValue.value)
  }
  inputVisible.value = false
  inputValue.value = ''
}

const handleClose = () => {
  visible.value = false
  resetForm()
}

const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
  Object.assign(form, {
    rating: 5,
    content: '',
    tags: [],
    recommend: true,
    suggestions: ''
  })
}

const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    loading.value = true

    const reviewData = {
      transaction_id: props.transaction.id,
      ...form
    }

    await submitReview(props.transaction.id, reviewData)

    ElMessage.success('评价提交成功')
    emit('success')
    handleClose()
  } catch (error) {
    console.error('提交评价失败:', error)
    ElMessage.error(error.message || '提交评价失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.dialog-footer {
  text-align: right;
}

.service-info {
  padding: 16px;
  background-color: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 16px;
}

.service-info h4 {
  margin: 0 0 8px 0;
  color: #303133;
  font-size: 16px;
  font-weight: 600;
}

.service-type {
  margin: 0 0 8px 0;
  color: #909399;
  font-size: 14px;
}

.service-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.provider,
.date {
  color: #909399;
  font-size: 13px;
}

.tag-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.predefined-tags,
.custom-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.el-rate {
  height: auto;
}
</style>

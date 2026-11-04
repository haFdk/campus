<template>
  <el-dialog
    v-model="visible"
    title="发布物品"
    width="600px"
    :before-close="handleClose"
    class="create-item-dialog"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="100px"
      class="item-form"
    >
      <el-form-item label="物品标题" prop="title">
        <el-input
          v-model="form.title"
          placeholder="请输入物品标题"
          maxlength="50"
          show-word-limit
        />
      </el-form-item>

      <el-form-item label="物品分类" prop="category">
        <el-select
          v-model="form.category"
          placeholder="请选择物品分类"
          style="width: 100%"
        >
          <el-option v-for="c in itemCategories" :key="c" :label="c" :value="c" />
        </el-select>
        <CategorySuggestion :title="form.title" :category="form.category" :active="visible" @apply="form.category = $event" />
      </el-form-item>

      <el-form-item label="物品描述（选填）" prop="description">
        <el-input
          v-model="form.description"
          type="textarea"
          :rows="4"
          placeholder="请详细描述物品的状况、特点等"
          maxlength="500"
          show-word-limit
        />
      </el-form-item>

      <el-form-item label="物品状态" prop="condition">
        <el-radio-group v-model="form.condition">
          <el-radio label="全新">全新</el-radio>
          <el-radio label="九成新">九成新</el-radio>
          <el-radio label="八成新">八成新</el-radio>
          <el-radio label="七成新">七成新</el-radio>
          <el-radio label="其他">其他</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="交易类型" prop="transaction_type">
        <el-radio-group v-model="form.transaction_type">
          <el-radio label="交换">交换</el-radio>
          <el-radio label="租赁">租赁</el-radio>
          <el-radio label="出售">出售</el-radio>
          <el-radio label="交换或出售">交换或出售</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item
        v-if="form.transaction_type === '租赁'"
        label="租赁价格"
        prop="rental_price_day"
      >
        <el-input-number
          v-model="form.rental_price_day"
          :min="0"
          :precision="2"
          placeholder="请输入每日租赁价格"
        />
        <span class="price-unit">元/天</span>
      </el-form-item>

      <el-form-item
        v-if="form.transaction_type === '出售' || form.transaction_type === '交换或出售'"
        label="出售价格"
        prop="sale_price"
      >
        <el-input-number
          v-model="form.sale_price"
          :min="0"
          :precision="2"
          placeholder="请输入出售价格"
        />
        <span class="price-unit">元</span>
      </el-form-item>

      <el-form-item label="校区" prop="location_campus">
        <el-input
          v-model="form.location_campus"
          placeholder="请输入所在校区"
        />
      </el-form-item>

      <el-form-item label="具体位置" prop="location_building">
        <el-input
          v-model="form.location_building"
          placeholder="请输入具体位置（如宿舍楼号）"
        />
      </el-form-item>

      <el-form-item label="物品图片">
        <el-upload
          ref="uploadRef"
          :file-list="fileList"
          :on-change="handleFileChange"
          :on-remove="handleFileRemove"
          :before-upload="beforeUpload"
          :auto-upload="false"
          list-type="picture-card"
          accept="image/*"
          :limit="5"
        >
          <el-icon><Plus /></el-icon>
          <template #tip>
            <div class="el-upload__tip">
              支持jpg/png格式，最多上传5张图片
            </div>
          </template>
        </el-upload>
      </el-form-item>

      <el-form-item
        v-if="form.transaction_type === '交换' || form.transaction_type === '交换或出售'"
        label="交换意向"
        prop="exchange_for"
      >
        <el-input
          v-model="form.exchange_for"
          type="textarea"
          :rows="3"
          placeholder="请描述您希望交换的物品类型或具体需求"
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
          发布物品
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { itemsAPI } from '@/api/items'
import CategorySuggestion from './CategorySuggestion.vue'
import { itemCategories } from '@/constants/itemCategories'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'success'])

const visible = ref(false)
const loading = ref(false)
const formRef = ref()
const uploadRef = ref()
const fileList = ref([])

const form = reactive({
  title: '',
  category: '',
  description: '',
  condition: '全新',
  transaction_type: '交换',
  exchange_for: '',
  rental_price_day: null,
  sale_price: null,
  location_campus: '',
  location_building: '',
  images: []
})

const rules = {
  title: [
    { required: true, message: '请输入物品标题', trigger: 'blur' },
    { min: 2, max: 50, message: '标题长度在 2 到 50 个字符', trigger: 'blur' }
  ],
  category: [
    { required: true, message: '请选择物品分类', trigger: 'change' }
  ],
  description: [{ max: 500, message: '描述不能超过 500 个字符', trigger: 'blur' }],
  condition: [
    { required: true, message: '请选择物品状态', trigger: 'change' }
  ],
  transaction_type: [
    { required: true, message: '请选择交易类型', trigger: 'change' }
  ],
  rental_price_day: [
    {
      validator: (rule, value, callback) => {
        if (form.transaction_type === '租赁' && (!value || value <= 0)) {
          callback(new Error('请输入有效的租赁价格'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  sale_price: [
    {
      validator: (rule, value, callback) => {
        if ((form.transaction_type === '出售' || form.transaction_type === '交换或出售') && (!value || value <= 0)) {
          callback(new Error('请输入有效的出售价格'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  exchange_for: [
    {
      validator: (rule, value, callback) => {
        if ((form.transaction_type === '交换' || form.transaction_type === '交换或出售') && (!value || value.trim() === '')) {
          callback(new Error('请输入交换意向'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

watch(() => props.modelValue, (val) => {
  visible.value = val
})

watch(visible, (val) => {
  emit('update:modelValue', val)
  if (!val) {
    resetForm()
  }
})

const handleClose = () => {
  visible.value = false
}

const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
  fileList.value = []
  form.images = []
  Object.assign(form, {
    title: '',
    category: '',
    description: '',
    condition: '全新',
    transaction_type: '交换',
    exchange_for: '',
    rental_price_day: null,
    sale_price: null,
    location_campus: '',
    location_building: '',
    images: []
  })
}

const beforeUpload = (file) => {
  const isImage = file.type.startsWith('image/')
  const isLt5M = file.size / 1024 / 1024 < 5

  if (!isImage) {
    ElMessage.error('只能上传图片文件!')
    return false
  }
  if (!isLt5M) {
    ElMessage.error('图片大小不能超过 5MB!')
    return false
  }
  return false // 阻止自动上传
}

const handleFileChange = (file, files) => {
  fileList.value = files
  // 转换为base64用于预览和提交
  const reader = new FileReader()
  reader.onload = (e) => {
    const index = files.findIndex(f => f.uid === file.uid)
    if (index !== -1) {
      form.images[index] = e.target.result
    }
  }
  reader.readAsDataURL(file.raw)
}

const handleFileRemove = (file, files) => {
  fileList.value = files
  const index = form.images.findIndex((_, i) => {
    return fileList.value[i]?.uid === file.uid
  })
  if (index !== -1) {
    form.images.splice(index, 1)
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    loading.value = true

    const itemData = {
      ...form,
      images: form.images.filter(img => img) // 过滤空值
    }

    await itemsAPI.createItem(itemData)

    ElMessage.success('物品发布成功！')
    emit('success')
    handleClose()
  } catch (error) {
    console.error('发布物品失败:', error)
    ElMessage.error(error.response?.data?.message || '发布失败，请重试')
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
@use "@/styles/variables.scss" as *;
.create-item-dialog {
  .item-form {
    .el-form-item {
      margin-bottom: 20px;
    }
  }

  .dialog-footer {
    text-align: right;

    .el-button {
      margin-left: 10px;
    }
  }

  :deep(.el-upload--picture-card) {
    width: 100px;
    height: 100px;
  }

  :deep(.el-upload-list--picture-card .el-upload-list__item) {
    width: 100px;
    height: 100px;
  }
}
</style>

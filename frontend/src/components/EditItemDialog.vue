<template>
  <el-dialog :model-value="modelValue" title="编辑物品" width="600px" @update:model-value="$emit('update:modelValue', $event)">
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item label="物品标题" prop="title"><el-input v-model="form.title" maxlength="50" /></el-form-item>
      <el-form-item label="分类" prop="category"><el-select v-model="form.category"><el-option v-for="c in categories" :key="c" :value="c" :label="c" /></el-select>
        <CategorySuggestion :title="form.title" :category="form.category" :active="modelValue" :item-key="item?.id" @apply="form.category = $event" />
      </el-form-item>
      <el-form-item label="物品描述（选填）" prop="description"><el-input v-model="form.description" type="textarea" :rows="3" maxlength="500" show-word-limit /></el-form-item>
      <el-form-item label="成色" prop="condition"><el-input v-model="form.condition" /></el-form-item>
      <el-form-item label="交易方式"><el-select v-model="form.transaction_type"><el-option v-for="t in ['交换','出售','租赁','交换或出售']" :key="t" :value="t" /></el-select></el-form-item>
      <el-form-item v-if="form.transaction_type?.includes('交换')" label="交换意向"><el-input v-model="form.exchange_for" /></el-form-item>
      <el-form-item v-if="form.transaction_type?.includes('出售')" label="售价"><el-input-number v-model="form.sale_price" :min="0.01" :precision="2" /></el-form-item>
      <el-form-item v-if="form.transaction_type === '租赁'" label="每日租金"><el-input-number v-model="form.rental_price_day" :min="0.01" :precision="2" /></el-form-item>
      <el-form-item label="校区"><el-input v-model="form.location_campus" /></el-form-item>
      <el-form-item label="交接地点"><el-input v-model="form.location_building" /></el-form-item>
      <el-form-item label="状态"><el-select v-model="form.status"><el-option v-for="(label, value) in statuses" :key="value" :label="label" :value="value" /></el-select></el-form-item>
      <el-form-item label="图片（最多 5 张，每张不超过 5MB）">
        <div class="pictures"><div v-for="(src, i) in form.images" :key="i"><img :src="src" alt="物品图片"><el-button text type="danger" @click="form.images.splice(i, 1)">移除</el-button></div></div>
        <input aria-label="添加图片" type="file" accept="image/*" @change="addImage">
      </el-form-item>
    </el-form>
    <template #footer><el-button @click="$emit('update:modelValue', false)">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存修改</el-button></template>
  </el-dialog>
</template>
<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { itemsAPI } from '@/api/items'
import CategorySuggestion from './CategorySuggestion.vue'
import { itemCategories as categories } from '@/constants/itemCategories'
const props = defineProps({ modelValue: Boolean, item: Object })
const emit = defineEmits(['update:modelValue', 'success'])
const formRef = ref()
const form = ref({ images: [] })
const saving = ref(false)
const statuses = { available:'在架', unavailable:'已下架', exchanged:'已交换', sold:'已售出', rented_out:'租借中' }
const rules = Object.fromEntries(['title','category','condition'].map(k => [k, [{required:true,message:'请填写此项',trigger:'blur'}]]))
rules.description = [{ validator: (_, value, done) => {
  if (value !== (props.item?.description || '') && (value || '').length > 500) done(new Error('描述不能超过 500 个字符'))
  else done()
}, trigger: 'blur' }]
watch(() => [props.modelValue, props.item?.id], ([value]) => {
  if (value && props.item) {
    const fields = ['title','description','category','condition','transaction_type','exchange_for','sale_price','rental_price_day','location_campus','location_building','status']
    form.value = Object.fromEntries(fields.map(k => [k, props.item[k]]))
    form.value.images = [...(props.item.images || [])]
  }
})
const addImage = (event) => {
  const file = event.target.files[0]
  event.target.value = ''
  if (!file) return
  if (!file.type.startsWith('image/') || file.size > 5 * 1024 * 1024 || form.value.images.length >= 5) {
    ElMessage.warning('请选择不超过 5MB 的图片，最多 5 张'); return
  }
  const reader = new FileReader()
  reader.onload = () => form.value.images.push(reader.result)
  reader.readAsDataURL(file)
}
const save = async () => {
  try {
    await formRef.value.validate()
    saving.value = true
    const payload = { id: props.item.id, ...form.value }
    if (payload.description === (props.item.description || '')) delete payload.description
    await itemsAPI.updateItem(payload)
    ElMessage.success('物品已更新')
    emit('success')
    emit('update:modelValue', false)
  } catch (error) {
    if (error?.response) ElMessage.error(error.response.data?.error || '保存失败')
  } finally { saving.value = false }
}
</script>
<style scoped>
.pictures { display: flex; gap: 10px; flex-wrap: wrap; width: 100%; }
.pictures > div { display: grid; }
.pictures img { width: 80px; height: 80px; object-fit: cover; }
</style>

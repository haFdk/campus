<template>
  <div class="category-suggestion" aria-live="polite">
    <el-button :loading="loading" :disabled="!active" @click="suggest">智能推荐分类</el-button>
    <span class="hint">实验性建议，可能分错；确认后才会更改分类</span>
    <div v-if="candidates.length" class="results" role="group" aria-label="建议分类">
      <div v-for="candidate in candidates" :key="candidate.category" class="result">
        <el-button size="small" type="primary" plain :aria-label="'选择分类：' + candidate.category" @click="apply(candidate.category)">
          {{ candidate.category }}
        </el-button>
        <span class="reason">{{ candidate.reason || '根据标题语义推荐' }}</span>
      </div>
    </div>
    <span v-if="candidates.length" class="hint">{{ sourceLabel }}</span>
    <p v-if="message" role="status">{{ message }}</p>
  </div>
</template>

<script setup>
import { computed, ref, watch, onBeforeUnmount } from 'vue'
import { itemsAPI } from '@/api/items'
import { itemCategories } from '@/constants/itemCategories'
const props = defineProps({ title: String, category: String, active: Boolean, itemKey: [String, Number] })
const emit = defineEmits(['apply'])
const loading = ref(false)
const candidates = ref([])
const source = ref('')
const sourceLabel = computed(() => ({
  hybrid: '词库匹配 · 模型辅助排序',
  lexicon: '当前为词库匹配建议，模型暂不可用',
  model: '根据标题语义推荐',
  legacy: '分类建议'
}[source.value] || '分类建议'))
const message = ref('')
let sequence = 0
let controller
function invalidate() {
  sequence++
  controller?.abort()
  loading.value = false
  candidates.value = []
  source.value = ''
  message.value = ''
}
watch(() => [props.title, props.category, props.active, props.itemKey], invalidate, { flush: 'sync' })
onBeforeUnmount(invalidate)
async function suggest() {
  if (loading.value || !props.active) return
  invalidate()
  if (!(props.title || '').trim()) {
    message.value = '请填写具体商品名称，如：高等数学教材、蓝牙耳机'
    return
  }
  const current = sequence
  controller = new AbortController()
  loading.value = true
  try {
    const { data } = await itemsAPI.suggestCategory({ title: props.title || '' }, controller.signal)
    if (current !== sequence || !props.active) return
    const rows = Array.isArray(data.candidates) ? data.candidates
      : (data.status === 'suggested' && data.category ? [{ category: data.category }] : [])
    const seen = new Set()
    candidates.value = rows.filter(row => {
      if (!row || !itemCategories.includes(row.category) || seen.has(row.category)) return false
      seen.add(row.category)
      return true
    }).slice(0, 3)
    source.value = data.source || 'legacy'
    message.value = data.message
  } catch (error) {
    if (current !== sequence) return
    message.value = error.response?.data?.error || '智能分类暂不可用或响应超时，请手动选择分类'
  } finally {
    if (current === sequence) loading.value = false
  }
}
function apply(category) {
  if (candidates.value.some(row => row.category === category) && props.active) {
    invalidate()
    emit('apply', category)
  }
}
</script>

<style scoped>
.category-suggestion { width: 100%; margin-top: 10px; line-height: 1.6; }
.hint { display: block; color: var(--el-text-color-secondary); font-size: 12px; margin-top: 5px; }
.results { display: grid; gap: 8px; margin-top: 10px; width: 100%; }
.result { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; padding: 8px; border: 1px solid var(--line); border-radius: 6px; background: var(--paper); }
.reason { font-size: 12px; line-height: 1.6; overflow-wrap: anywhere; color: var(--el-text-color-secondary); }
p { color: var(--el-text-color-secondary); font-size: 13px; margin: 5px 0 0; }
</style>

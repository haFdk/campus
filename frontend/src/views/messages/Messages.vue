<template>
  <div class="messages-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">
          <el-icon><ChatDotRound /></el-icon>
          消息中心
        </h1>
        <p class="page-description">与其他用户交流沟通</p>
      </div>
    </div>

    <div class="messages-container">
      <el-row :gutter="0" class="messages-layout">
        <!-- 对话列表 -->
        <el-col :lg="8" :md="10" :sm="24" class="conversations-panel">
          <el-card class="conversations-card">
            <template #header>
              <div class="conversations-header">
                <span>对话列表</span>
                <el-badge :value="unreadCount" :hidden="unreadCount === 0" />
              </div>
            </template>

            <!-- 搜索框 -->
            <div class="search-section">
              <el-input
                v-model="searchKeyword"
                placeholder="搜索联系人"
                clearable
                @input="filterConversations"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
            </div>

            <!-- 对话列表 -->
            <div class="conversations-list">
              <div v-if="loading" class="loading-container">
                <el-skeleton :rows="5" animated />
              </div>

              <div v-else-if="filteredConversations.length > 0">
                <div
                  v-for="conversation in filteredConversations"
                  :key="conversation.id"
                  class="conversation-item"
                  :class="{ active: selectedConversation?.id === conversation.id }"
                  @click="selectConversation(conversation)"
                >
                  <div class="conversation-avatar">
                    <el-badge
                      :value="conversation.unread_count"
                      :hidden="conversation.unread_count === 0"
                      class="unread-badge"
                    >
                      <el-avatar :size="40" :src="conversation.other_user?.avatar_url">
                        {{ conversation.other_user?.username?.charAt(0) }}
                      </el-avatar>
                    </el-badge>
                  </div>

                  <div class="conversation-content">
                    <div class="conversation-header">
                      <span class="user-name">{{ conversation.other_user?.username }}</span>
                      <span class="last-time">
                        {{ conversation.last_message_time ? formatRelativeTime(conversation.last_message_time) : '' }}
                      </span>
                    </div>

                    <div class="last-message">
                      <span
                        class="message-text"
                        :class="{ unread: conversation.unread_count > 0 }"
                      >
                        {{ conversation.last_message || '暂无消息' }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <div v-else class="no-conversations">
                <el-empty description="暂无对话" />
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- 聊天区域 -->
        <el-col :lg="16" :md="14" :sm="24" class="chat-panel">
          <el-card class="chat-card">
            <!-- 聊天头部 -->
            <template #header>
              <div v-if="selectedConversation" class="chat-header">
                <div class="chat-user-info">
                  <el-avatar :size="32" :src="selectedConversation.other_user?.avatar_url">
                    {{ selectedConversation.other_user?.username?.charAt(0) }}
                  </el-avatar>
                  <span class="chat-user-name">{{ selectedConversation.other_user?.username }}</span>
                </div>

              </div>
              <div v-else class="no-chat-header">
                <span>选择一个对话开始聊天</span>
              </div>
            </template>

            <!-- 聊天内容 -->
            <div class="chat-content">
              <div v-if="selectedConversation" class="messages-container">
                <!-- 消息列表 -->
                <div ref="messagesContainer" class="messages-list">
                  <div v-if="messagesLoading" class="messages-loading">
                    <el-skeleton :rows="3" animated />
                  </div>

                  <div v-else-if="messages.length > 0">
                    <div
                      v-for="message in messages"
                      :key="message.id"
                      class="message-item"
                      :class="{ 'is-mine': message.sender_id === currentUserId }"
                    >
                      <div class="message-avatar">
                        <el-avatar :size="28" :src="message.sender?.avatar_url">
                          {{ message.sender?.username?.charAt(0) }}
                        </el-avatar>
                      </div>

                      <div class="message-content">
                        <div class="message-bubble">
                          <p class="message-text">{{ message.content }}</p>
                        </div>
                        <div class="message-time">
                          {{ formatMessageTime(message.created_at) }}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div v-else class="no-messages">
                    <el-empty description="暂无消息，开始对话吧" />
                  </div>
                </div>

                <!-- 消息输入 -->
                <div class="message-input-container">
                  <div class="input-area">
                    <el-input
                      v-model="newMessage"
                      type="textarea"
                      :rows="3"
                      placeholder="输入消息内容..."
                      resize="none"
                      @keydown.enter.exact="sendMessage"
                      @keydown.enter.shift.exact.prevent="newMessage += '\n'"
                    />
                  </div>

                  <div class="input-actions">
                    <el-button
                      type="primary"
                      :loading="sending"
                      :disabled="!newMessage.trim()"
                      @click="sendMessage"
                    >
                      发送
                    </el-button>
                  </div>
                </div>
              </div>

              <!-- 未选择对话 -->
              <div v-else class="no-chat-selected">
                <el-empty description="选择一个对话开始聊天">
                  <el-icon class="chat-icon"><ChatDotRound /></el-icon>
                </el-empty>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { messagesAPI } from '@/api/messages'
import { authAPI } from '@/api/auth'
import { formatRelativeTime } from '@/utils'
import { ElMessage } from 'element-plus'
import {
  ChatDotRound,
  Search
} from '@element-plus/icons-vue'

const route = useRoute()
const authStore = useAuthStore()

// 响应式数据
const loading = ref(false)
const messagesLoading = ref(false)
const sending = ref(false)
const conversations = ref([])
const filteredConversations = ref([])
const selectedConversation = ref(null)
const messages = ref([])
const newMessage = ref('')
const searchKeyword = ref('')
const messagesContainer = ref()

// 计算属性
const currentUserId = computed(() => authStore.user?.id)
const unreadCount = computed(() => {
  return conversations.value.reduce((total, conv) => total + (conv.unread_count || 0), 0)
})

// 获取对话列表
const getConversations = async () => {
  try {
    loading.value = true
    const response = await messagesAPI.getConversations()
    conversations.value = response.data.conversations.map(conversation => ({
      ...conversation,
      last_message: conversation.last_message_text || conversation.last_message?.content_excerpt,
      last_message_time: conversation.last_message_time || conversation.last_message?.created_at
    }))
    filteredConversations.value = conversations.value

    // 如果URL中有用户参数，自动选择对话
    if (route.query.user) {
      const targetConversation = conversations.value.find(
        conv => conv.other_user.id === parseInt(route.query.user)
      )
      if (targetConversation) selectConversation(targetConversation)
      else await openNewConversation(parseInt(route.query.user))
    }
  } catch (error) {
    console.error('获取对话列表失败:', error)
    ElMessage.error('获取对话列表失败')
  } finally {
    loading.value = false
  }
}

// 选择对话
const selectConversation = async (conversation) => {
  selectedConversation.value = conversation
  await getMessages(conversation.other_user.id)

  // 标记消息为已读
  if (conversation.unread_count > 0) {
    markAsRead(conversation.other_user.id)
  }
}

// 获取消息列表
const getMessages = async (conversationId) => {
  try {
    messagesLoading.value = true
    const response = await messagesAPI.getConversationMessages(conversationId)
    messages.value = [...(response.data.items || [])].reverse()

    // 滚动到底部
    nextTick(() => {
      scrollToBottom()
    })
  } catch (error) {
    console.error('获取消息列表失败:', error)
    ElMessage.error('获取消息列表失败')
  } finally {
    messagesLoading.value = false
  }
}

// 发送消息
const sendMessage = async () => {
  if (!newMessage.value.trim() || !selectedConversation.value) return

  try {
    sending.value = true
    const messageData = {
      receiver_id: selectedConversation.value.other_user.id,
      content: newMessage.value.trim()
    }

    const response = await messagesAPI.sendMessage(messageData)

    // 添加到消息列表
    messages.value.push(response.data.chat_message)

    // 更新对话列表中的最后消息
    const conversation = conversations.value.find(
      c => c.other_user.id === selectedConversation.value.other_user.id
    )
    if (conversation) {
      conversation.last_message = newMessage.value.trim()
      conversation.last_message_time = new Date().toISOString()
    }

    // 清空输入框
    newMessage.value = ''

    // 滚动到底部
    nextTick(() => {
      scrollToBottom()
    })
  } catch (error) {
    console.error('发送消息失败:', error)
    ElMessage.error('发送消息失败')
  } finally {
    sending.value = false
  }
}

// 标记为已读
const markAsRead = async (conversationId) => {
  try {
    await messagesAPI.markConversationAsRead(conversationId)

    // 更新本地未读数
    const conversation = conversations.value.find(c => c.other_user.id === conversationId)
    if (conversation) {
      conversation.unread_count = 0
    }
  } catch (error) {
    console.error('标记已读失败:', error)
  }
}

// 过滤对话
const filterConversations = () => {
  if (!searchKeyword.value.trim()) {
    filteredConversations.value = conversations.value
  } else {
    filteredConversations.value = conversations.value.filter(conv =>
      conv.other_user.username.toLowerCase().includes(searchKeyword.value.toLowerCase())
    )
  }
}

const openNewConversation = async (userId) => {
  if (!userId || userId === currentUserId.value) return
  try {
    const { data: user } = await authAPI.getPublicUser(userId)
    const conversation = {
      id: user.id,
      other_user: user,
      last_message: '',
      last_message_time: null,
      unread_count: 0
    }
    conversations.value.unshift(conversation)
    filteredConversations.value = conversations.value
    await selectConversation(conversation)
  } catch (error) {
    console.error('无法创建对话:', error)
  }
}

// 滚动到底部
const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// 格式化消息时间
const formatMessageTime = (time) => {
  const date = new Date(time)
  const now = new Date()
  const diff = now - date

  if (diff < 24 * 60 * 60 * 1000) {
    // 24小时内显示时间
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  } else {
    // 超过24小时显示日期
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
  }
}

// 监听路由变化
watch(() => route.query.user, (newUserId) => {
  if (newUserId && conversations.value.length > 0) {
    const targetConversation = conversations.value.find(
      conv => conv.other_user.id === parseInt(newUserId)
    )
    if (targetConversation) selectConversation(targetConversation)
    else openNewConversation(parseInt(newUserId))
  }
})

// 初始化
onMounted(() => {
  getConversations()
})
</script>

<style lang="scss" scoped>
@use "@/styles/variables.scss" as *;

.messages-page {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
  height: calc(100vh - 120px);
}

.page-header {
  margin-bottom: 24px;

  .header-content {
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

.messages-container {
  height: calc(100% - 100px);

  .messages-layout {
    height: 100%;
  }
}

.conversations-panel {
  height: 100%;
  border-right: 1px solid $border-color-lighter;

  .conversations-card {
    height: 100%;

    :deep(.el-card__body) {
      height: calc(100% - 60px);
      padding: 0;
      display: flex;
      flex-direction: column;
    }

    .conversations-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .search-section {
      padding: 16px;
      border-bottom: 1px solid $border-color-lighter;
    }

    .conversations-list {
      flex: 1;
      overflow-y: auto;

      .loading-container {
        padding: 16px;
      }

      .conversation-item {
        display: flex;
        align-items: center;
        padding: 12px 16px;
        cursor: pointer;
        border-bottom: 1px solid $border-color-lighter;
        transition: background-color 0.3s ease;

        &:hover {
          background-color: $bg-color-light;
        }

        &.active {
          background-color: $color-primary-light;
          border-right: 3px solid $color-primary;
        }

        .conversation-avatar {
          margin-right: 12px;

          .unread-badge {
            :deep(.el-badge__content) {
              top: 5px;
              right: 5px;
            }
          }
        }

        .conversation-content {
          flex: 1;
          min-width: 0;

          .conversation-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 4px;

            .user-name {
              font-weight: 500;
              color: $text-color-primary;
            }

            .last-time {
              font-size: 12px;
              color: $text-color-secondary;
            }
          }

          .last-message {
            .message-text {
              font-size: 14px;
              color: $text-color-secondary;
              display: -webkit-box;
              -webkit-line-clamp: 1;
              -webkit-box-orient: vertical;
              overflow: hidden;

              &.unread {
                font-weight: 500;
                color: $text-color-primary;
              }
            }
          }
        }
      }

      .no-conversations {
        padding: 40px 20px;
        text-align: center;
      }
    }
  }
}

.chat-panel {
  height: 100%;

  .chat-card {
    height: 100%;

    :deep(.el-card__body) {
      height: calc(100% - 60px);
      padding: 0;
    }

    .chat-header {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .chat-user-info {
        display: flex;
        align-items: center;
        gap: 12px;

        .chat-user-name {
          font-weight: 500;
          color: $text-color-primary;
        }
      }
    }

    .no-chat-header {
      text-align: center;
      color: $text-color-secondary;
    }

    .chat-content {
      height: 100%;

      .messages-container {
        height: 100%;
        display: flex;
        flex-direction: column;

        .messages-list {
          flex: 1;
          overflow-y: auto;
          padding: 16px;

          .messages-loading {
            padding: 20px;
          }

          .message-item {
            display: flex;
            margin-bottom: 16px;

            &.is-mine {
              flex-direction: row-reverse;

              .message-content {
                align-items: flex-end;

                .message-bubble {
                  background-color: $color-primary;
                  color: white;
                }
              }
            }

            .message-avatar {
              margin: 0 8px;
            }

            .message-content {
              display: flex;
              flex-direction: column;
              max-width: 70%;

              .message-bubble {
                background-color: $bg-color-light;
                border-radius: 12px;
                padding: 8px 12px;
                margin-bottom: 4px;

                .message-text {
                  margin: 0;
                  line-height: 1.4;
                  white-space: pre-wrap;
                }
              }

              .message-time {
                font-size: 12px;
                color: $text-color-secondary;
                padding: 0 4px;
              }
            }
          }

          .no-messages {
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
          }
        }

        .message-input-container {
          border-top: 1px solid $border-color-lighter;
          padding: 16px;

          .input-toolbar {
            display: flex;
            gap: 8px;
            margin-bottom: 12px;
          }

          .input-area {
            margin-bottom: 12px;

            :deep(.el-textarea__inner) {
              resize: none;
              border-radius: 8px;
            }
          }

          .input-actions {
            display: flex;
            justify-content: flex-end;
          }
        }
      }

      .no-chat-selected {
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;

        .chat-icon {
          font-size: 64px;
          color: $text-color-placeholder;
          margin-bottom: 16px;
        }
      }
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .messages-page {
    padding: 16px;
    height: calc(100vh - 100px);
  }

  .conversations-panel {
    border-right: none;
    border-bottom: 1px solid $border-color-lighter;
  }

  .messages-layout {
    :deep(.el-col) {
      margin-bottom: 16px;
    }
  }
}
</style>

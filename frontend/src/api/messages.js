import request from './request'

// 获取消息列表
export const getMessages = (params = {}) => {
  return request.get('/messages', { params })
}

// 获取消息详情
export const getMessageById = (id) => {
  return request.get(`/messages/${id}`)
}

// 发送消息
export const sendMessage = (data) => {
  return request.post('/messages', data)
}

// 标记消息为已读
export const markAsRead = (id) => {
  return request.put(`/messages/${id}/read`)
}

// 删除消息
export const deleteMessage = (id) => {
  return request.delete(`/messages/${id}`)
}

// 获取未读消息数量
export const getUnreadCount = () => {
  return request.get('/messages/unread-count')
}

// 获取与特定用户的对话
export const getConversation = (userId, params = {}) => {
  return request.get(`/messages/conversation/${userId}`, { params })
}

// 获取对话列表
export const getConversations = (params = {}) => {
  return request.get('/messages/conversations', { params })
}

// 获取对话消息
export const getConversationMessages = (conversationId, params = {}) => {
  return request.get(`/messages/conversation/${conversationId}`, { params })
}

export const markConversationAsRead = (userId) => {
  return request.post(`/messages/conversation/${userId}/mark_read`)
}

// 保持向后兼容
export const messagesAPI = {
  getMessages,
  getMessageById,
  sendMessage,
  markAsRead,
  deleteMessage,
  getUnreadCount,
  getConversation,
  getConversations,
  getConversationMessages,
  markConversationAsRead
}

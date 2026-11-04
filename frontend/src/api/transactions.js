import request from './request'

// 获取交易列表
export const getTransactions = (params = {}) => {
  return request.get('/transactions', { params })
}

// 获取交易详情
export const getTransactionById = (id) => {
  return request.get(`/transactions/${id}`)
}

// 完成交易
export const completeTransaction = (id) => {
  return request.put(`/transactions/${id}/complete`)
}

// 取消交易
export const cancelTransaction = (id) => {
  return request.put(`/transactions/${id}/cancel`)
}

// 响应交易请求（接受或拒绝）
export const respondToTransaction = (id, data) => {
  return request.put(`/transactions/${id}/respond`, data)
}

// 获取用户的交易记录
export const getUserTransactions = (userId, params = {}) => {
  return request.get(`/users/${userId}/transactions`, { params })
}

// 创建交换请求
export const createExchangeRequest = (data) => {
  return request.post('/transactions/exchange-requests', data)
}

// 获取交换请求列表
export const getExchangeRequests = (params = {}) => {
  return request.get('/transactions/exchange-requests', { params })
}

// 响应交换请求
export const respondToExchangeRequest = (id, data) => {
  return request.put(`/transactions/exchange-requests/${id}/respond`, data)
}

export const transactionsAPI = {
  getTransactions,
  getTransactionById,
  completeTransaction,
  cancelTransaction,
  respondToTransaction,
  getUserTransactions,
  createExchangeRequest,
  getExchangeRequests,
  respondToExchangeRequest
}
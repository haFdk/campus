import request from './request'

// 获取物品列表
const getItems = (params = {}) => {
  return request.get('/items', { params })
}

// 获取物品详情
const getItemById = (id) => {
  return request.get(`/items/${id}`)
}

// 创建物品
const createItem = (data) => {
  return request.post('/items', data)
}

// 更新物品
const updateItem = (data) => {
  return request.put(`/items/${data.id}`, data)
}

// 删除物品
const deleteItem = (id) => {
  return request.delete(`/items/${id}`)
}

// 获取用户的物品
const getUserItems = (userId, params = {}) => {
  return request.get(`/users/${userId}/items`, { params })
}

const getMyItems = (params = {}) => {
  return request.get('/items/mine', { params })
}

// 请求物品交换
const requestItemExchange = (data) => {
  return request.post('/items/exchange-request', data)
}

// 响应交换请求
const respondToExchangeRequest = (requestId, data) => {
  return request.put(`/items/exchange-request/${requestId}`, data)
}

// 获取物品交换请求
const getExchangeRequests = (params = {}) => {
  return request.get('/items/exchange-requests', { params })
}

export const itemsAPI = {
  suggestCategory: (data, signal) => request.post('/items/category-suggestion', data, { signal, timeout: 45000, silentError: true }),
  getItems,
  getItemById,
  createItem,
  updateItem,
  deleteItem,
  getUserItems,
  getMyItems,
  requestItemExchange,
  respondToExchangeRequest,
  getExchangeRequests
}

export default itemsAPI;

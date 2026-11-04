import request from './request'

// 提交评价
export const submitReview = (transactionId, data) => {
  return request.post(`/transactions/${transactionId}/reviews`, data)
}

// 获取收到的评价
export const getReceivedReviews = (params = {}) => {
  return request.get('/reviews/received', { params })
}

// 获取发出的评价
export const getGivenReviews = (params = {}) => {
  return request.get('/reviews/given', { params })
}

// 回复评价
export const replyToReview = (reviewId, data) => {
  return request.post(`/reviews/${reviewId}/reply`, data)
}

// 更新评价
export const updateReview = (reviewId, data) => {
  return request.put(`/reviews/${reviewId}`, data)
}

// 删除评价
export const deleteReview = (reviewId) => {
  return request.delete(`/reviews/${reviewId}`)
}

// 获取用户评价列表
export const getUserReviews = (userId, params = {}) => {
  return request.get(`/users/${userId}/reviews`, { params })
}

// 获取物品评价列表
export const getItemReviews = (itemId, params = {}) => {
  return request.get(`/items/${itemId}/reviews`, { params })
}

// 获取评价详情
export const getReviewById = (id) => {
  return request.get(`/reviews/${id}`)
}

export const reviewsAPI = {
  submitReview,
  getReceivedReviews,
  getGivenReviews,
  replyToReview,
  updateReview,
  deleteReview,
  getUserReviews,
  getItemReviews,
  getReviewById
}

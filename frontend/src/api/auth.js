import request from './request'

// 用户注册
export const register = (data) => {
  return request.post('/auth/register', data)
}

// 用户登录
export const login = (data) => {
  return request.post('/auth/login', data)
}

// 获取当前用户信息
export const getCurrentUser = () => {
  return request.get('/auth/me')
}

// 更新用户资料
export const updateProfile = (data) => {
  return request.put('/auth/profile', data)
}

// 修改密码
export const changePassword = (data) => {
  return request.put('/auth/change-password', data)
}

// 发送手机验证码
export const sendPhoneVerificationCode = (data) => {
  return request.post('/auth/send-phone-verification', data)
}

// 验证手机号
export const verifyPhone = (data) => {
  return request.post('/auth/verify-phone', data)
}

// 发送邮箱验证
export const sendVerificationEmail = () => {
  return request.post('/auth/send-verification-email')
}

// 获取用户资料
export const getUserProfile = () => {
  return request.get('/auth/profile')
}

// 获取用户统计
export const getUserStats = () => {
  return request.get('/auth/stats')
}

export const getPublicUser = (userId) => {
  return request.get(`/users/${userId}`)
}

// 保持向后兼容
export const authAPI = {
  register,
  login,
  getCurrentUser,
  updateProfile,
  changePassword,
  sendPhoneVerificationCode,
  verifyPhone,
  sendVerificationEmail,
  getUserProfile,
  getUserStats,
  getPublicUser
}

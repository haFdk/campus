import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authAPI } from '@/api/auth'
import { setToken, removeToken, getToken } from '@/utils/auth'
import { ElMessage } from 'element-plus'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const token = ref(getToken())

  const isAuthenticated = computed(() => !!token.value)
  const isLoggedIn = computed(() => isAuthenticated.value)

  // 登录
  const login = async (credentials) => {
    try {
      const response = await authAPI.login(credentials)
      const { access_token, user: userData } = response.data

      // 先设置到cookie，确保getToken()能立即获取到
      setToken(access_token)
      // 再设置到store
      token.value = access_token
      user.value = userData

      ElMessage.success('登录成功')
      return { success: true }
    } catch (error) {
      ElMessage.error(error.response?.data?.message || '登录失败')
      return { success: false, error }
    }
  }

  // 注册
  const register = async (userData) => {
    try {
      await authAPI.register(userData)
      ElMessage.success('注册成功，请登录')
      return { success: true }
    } catch (error) {
      ElMessage.error(error.response?.data?.message || '注册失败')
      return { success: false, error }
    }
  }

  // 获取当前用户信息
  const getCurrentUser = async () => {
    try {
      const response = await authAPI.getCurrentUser()
      user.value = response.data
      return { success: true }
    } catch (error) {
      console.error('获取用户信息失败:', error)
      // 不要在这里自动登出，让请求拦截器处理JWT错误
      // 只有在确实需要时才清除用户信息
      if (error.response?.status === 401 ||
          (error.response?.status === 422 &&
           error.response?.data?.error?.includes('token'))) {
        // JWT相关错误，清除本地状态但不显示消息（由拦截器处理）
        token.value = null
        user.value = null
        removeToken()
      }
      return { success: false, error }
    }
  }

  // 更新用户资料
  const updateProfile = async (profileData) => {
    try {
      const response = await authAPI.updateProfile(profileData)
      user.value = { ...user.value, ...(response.data.user || response.data) }
      ElMessage.success('资料更新成功')
      return { success: true }
    } catch (error) {
      ElMessage.error(error.response?.data?.message || '更新失败')
      return { success: false, error }
    }
  }

  // 登出
  const logout = async () => {
    try { await authAPI.logout() } catch { /* Always clear local credentials. */ }
    token.value = null
    user.value = null
    removeToken()
    ElMessage.success('已退出登录')
  }

  // 初始化时获取用户信息
  const init = async () => {
    if (token.value) {
      await getCurrentUser()
    }
  }

  return {
    user,
    token,
    isAuthenticated,
    isLoggedIn,
    login,
    register,
    getCurrentUser,
    updateProfile,
    logout,
    init
  }
})

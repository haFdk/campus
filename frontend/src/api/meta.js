import request from './request'

export const getPlatformStats = () => request.get('/stats')
export const getHealth = () => request.get('/health')

export const metaAPI = {
  getPlatformStats,
  getHealth
}

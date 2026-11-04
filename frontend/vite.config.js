import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  publicDir: 'public',  // 明确指定public目录为静态资源目录
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api/v1': {
        target: process.env.VITE_API_TARGET || 'http://127.0.0.1:5000',
        changeOrigin: true,
        secure: false
      }
    }
  },
  css: {
    preprocessorOptions: {
      scss: {
        api: 'modern-compiler',
        silenceDeprecations: ['legacy-js-api', 'import']
      }
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          // Keep shared Vue / Element Plus dependencies in one chunk.
          // Splitting them by package name can create circular chunk imports
          // that fail at module initialization even when vite build succeeds.
          if (id.includes('node_modules')) return 'vendor'
        }
      }
    }
  }
})

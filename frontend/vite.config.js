import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Vite（開発サーバー兼ビルドツール）の設定
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
})

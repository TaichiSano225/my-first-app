import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Vite（開発サーバー兼ビルドツール）の設定
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // 開発時、/api で始まる呼び出しをバックエンド(FastAPI)へ転送する。
    // バックエンドの API も /api 配下なので、パスはそのまま渡す。
    // 例: /api/stock/AAPL → http://localhost:8000/api/stock/AAPL
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})

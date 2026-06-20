// API はすべて /api 配下にリクエストする。
// - 開発時: Vite が /api をバックエンド(localhost:8000)へ中継（vite.config.js）
// - 本番(Docker)時: nginx が /api をバックエンドコンテナへ中継（nginx.conf）
export const API_BASE = '/api'

// 数値の頭に符号を付ける（プラスなら "+"、マイナスは元から "-" が付く）
// 例: 2.52 → "+2.52" / -1.3 → "-1.3"
export function formatSigned(n) {
  const sign = n >= 0 ? '+' : ''
  return sign + n.toLocaleString()
}

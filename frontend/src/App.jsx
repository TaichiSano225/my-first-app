import { useState } from 'react'

// API はすべて /api 配下にリクエストする。
// - 開発時: Vite が /api をバックエンド(localhost:8000)へ中継（vite.config.js）
// - 本番(Docker)時: nginx が /api をバックエンドコンテナへ中継（nginx.conf）
const API_BASE = '/api'

// 数値の頭に符号を付ける（プラスなら "+"、マイナスは元から "-" が付く）
// 例: 2.52 → "+2.52" / -1.3 → "-1.3"
function formatSigned(n) {
  const sign = n >= 0 ? '+' : ''
  return sign + n.toLocaleString()
}

export default function App() {
  const [query, setQuery] = useState('')       // 入力欄の文字列
  const [result, setResult] = useState(null)   // 取得した株価 {symbol, price}
  const [error, setError] = useState('')        // エラーメッセージ
  const [loading, setLoading] = useState(false) // 検索中かどうか

  async function handleSearch(e) {
    e.preventDefault() // フォーム送信時のページ再読み込みを止める
    const symbol = query.trim()
    if (!symbol) return

    setLoading(true)
    setError('')
    setResult(null)

    try {
      // FastAPI の /stock/{symbol} を呼び出す
      const res = await fetch(`${API_BASE}/stock/${encodeURIComponent(symbol)}`)
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || '株価を取得できませんでした。')
      }
      const data = await res.json()
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container">
      <h1>株価チェッカー</h1>

      {/* 銘柄入力欄 ＋ 検索ボタン */}
      <form className="search" onSubmit={handleSearch}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="銘柄を入力 (例: AAPL, トヨタ)"
        />
        <button type="submit" disabled={loading}>
          {loading ? '検索中...' : '検索'}
        </button>
      </form>

      {/* エラー表示 */}
      {error && <p className="error">{error}</p>}

      {/* 株価表示 */}
      {result && (
        <div className="result">
          {/* 会社名（取れなければティッカーを表示） */}
          <div className="name">{result.name || result.symbol}</div>
          <div className="symbol">{result.symbol}</div>

          {/* 現在価格 */}
          <div className="price">{result.price.toLocaleString()}</div>
          <div className="label">現在価格</div>

          {/* 前日終値・前日比 */}
          <dl className="details">
            {result.prev_close != null && (
              <div className="row">
                <dt>前日終値</dt>
                <dd>{result.prev_close.toLocaleString()}</dd>
              </div>
            )}
            {result.change != null && (
              <div className="row">
                <dt>前日比</dt>
                {/* up=プラスは緑、down=マイナスは赤 */}
                <dd className={result.change >= 0 ? 'up' : 'down'}>
                  {formatSigned(result.change)}
                  {result.change_pct != null &&
                    ` (${formatSigned(result.change_pct)}%)`}
                </dd>
              </div>
            )}
          </dl>
        </div>
      )}
    </div>
  )
}

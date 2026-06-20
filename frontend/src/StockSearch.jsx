import { useState } from 'react'
import { API_BASE, formatSigned } from './utils.js'

// 銘柄を1つ検索して株価を表示する画面
export default function StockSearch() {
  const [query, setQuery] = useState('')       // 入力欄の文字列
  const [result, setResult] = useState(null)   // 取得した株価
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
    <div>
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

      {error && <p className="error">{error}</p>}

      {/* 株価表示 */}
      {result && (
        <div className="result">
          <div className="name">{result.name || result.symbol}</div>
          <div className="symbol">{result.symbol}</div>

          <div className="price">{result.price.toLocaleString()}</div>
          <div className="label">現在価格</div>

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

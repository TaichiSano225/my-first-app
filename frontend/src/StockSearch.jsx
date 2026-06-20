import { useEffect, useState } from 'react'
import { API_BASE, formatSigned, timingClass } from './utils.js'
import RangeBar from './RangeBar.jsx'

// 銘柄を1つ検索して、株価・買い時・アナリスト予想・企業概要・ニュースを表示する画面
export default function StockSearch({ initialQuery = '' }) {
  const [query, setQuery] = useState(initialQuery)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function runSearch(symbol) {
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
      setResult(await res.json())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // 別タブから ?q=銘柄 で開かれたときは自動で検索する
  useEffect(() => {
    if (initialQuery) runSearch(initialQuery)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialQuery])

  function handleSearch(e) {
    e.preventDefault()
    runSearch(query.trim())
  }

  const up = result && result.change != null && result.change >= 0

  return (
    <div>
      <form className="field" onSubmit={handleSearch}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="会社名でもOK（例: apple / トヨタ / nvidia）"
        />
        <button type="submit" disabled={loading}>
          {loading ? '取得中…' : '検索'}
        </button>
      </form>

      {error && <p className="error">{error}</p>}
      {loading && <p className="hint">株価とニュースを取得しています…</p>}

      {result && (
        <div className="detail">
          {/* ヘッダー：社名・ティッカー・業界 */}
          <div className="detail-head">
            <h2 className="detail-name">{result.name || result.symbol}</h2>
            <div className="chips">
              <span className="chip chip-ticker">{result.symbol}</span>
              {result.sector && <span className="chip">{result.sector}</span>}
              {result.industry && <span className="chip chip-soft">{result.industry}</span>}
            </div>
          </div>

          {/* 価格 + 前日比 + 買い時バッジ */}
          <div className="price-block">
            <div>
              <div className="price-big">
                {result.price.toLocaleString()}
                <span className="price-cur">{result.currency}</span>
              </div>
              {result.change != null && (
                <div className={`price-change ${up ? 'pos' : 'neg'}`}>
                  {up ? '▲' : '▼'} {formatSigned(result.change)}
                  {result.change_pct != null && ` (${formatSigned(result.change_pct)}%)`}
                </div>
              )}
            </div>
            <span className={`timing timing-${timingClass(result.timing_label)}`}>
              {result.timing_label}
            </span>
          </div>
          {result.timing_reason && <p className="timing-reason">{result.timing_reason}</p>}

          {/* 52週レンジ */}
          <RangeBar
            pct={result.range_pct}
            low={result.low_52w}
            high={result.high_52w}
            currency={result.currency}
          />

          {/* 買い時の根拠（文章での説明） */}
          {result.timing_detail && (
            <div className="panel timing-panel">
              <h3 className="panel-title">
                買い時の根拠
                <span className={`timing timing-${timingClass(result.timing_label)}`}>
                  {result.timing_label}
                </span>
              </h3>
              <p className="summary">{result.timing_detail}</p>
              {/* なぜ株価が動いたかの考察（推測） */}
              {result.movement_analysis && (
                <div className="analysis">
                  <span className="analysis-label">値動きの考察（推測）</span>
                  <p className="summary">{result.movement_analysis}</p>
                </div>
              )}
            </div>
          )}

          {/* 今後の予想（アナリスト目標株価） */}
          {(result.target_mean != null || result.rec_label) && (
            <div className="panel">
              <h3 className="panel-title">今後の予想（アナリスト）</h3>
              <div className="stat-grid">
                <div className="stat">
                  <span className="stat-label">評価</span>
                  <span className="stat-value">{result.rec_label || '—'}</span>
                </div>
                <div className="stat">
                  <span className="stat-label">目標株価（平均）</span>
                  <span className="stat-value">
                    {result.target_mean != null
                      ? result.target_mean.toLocaleString()
                      : '—'}
                  </span>
                </div>
                <div className="stat">
                  <span className="stat-label">上振れ余地</span>
                  <span
                    className={`stat-value ${
                      result.upside != null ? (result.upside >= 0 ? 'pos' : 'neg') : ''
                    }`}
                  >
                    {result.upside != null ? `${formatSigned(result.upside)}%` : '—'}
                  </span>
                </div>
                <div className="stat">
                  <span className="stat-label">目標レンジ</span>
                  <span className="stat-value sm">
                    {result.target_low != null && result.target_high != null
                      ? `${result.target_low.toLocaleString()} – ${result.target_high.toLocaleString()}`
                      : '—'}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* どんな企業か */}
          {result.summary && (
            <div className="panel">
              <h3 className="panel-title">どんな企業？</h3>
              <p className="summary">{result.summary}</p>
            </div>
          )}

          {/* 最近のトピック */}
          {result.news && result.news.length > 0 && (
            <div className="panel">
              <h3 className="panel-title">最近のトピック</h3>
              <ul className="news">
                {result.news.map((n, i) => (
                  <li key={i}>
                    {n.link ? (
                      <a href={n.link} target="_blank" rel="noreferrer">
                        {n.title}
                      </a>
                    ) : (
                      <span>{n.title}</span>
                    )}
                    {n.publisher && <span className="news-src">{n.publisher}</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <p className="disclaimer">
            ※ Yahoo Finance のデータに基づく参考情報です。投資はご自身の判断と責任で行ってください。
          </p>
        </div>
      )}
    </div>
  )
}

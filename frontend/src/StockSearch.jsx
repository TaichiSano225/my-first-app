import { useEffect, useState } from 'react'
import { API_BASE, formatSigned, timingClass } from './utils.js'
import { isWatched, toggleWatch } from './store.js'
import RangeBar from './RangeBar.jsx'
import Chart from './Chart.jsx'
import Summary from './Summary.jsx'

// 銘柄を1つ検索して、株価・買い時・アナリスト予想・企業概要・ニュースを表示する画面
export default function StockSearch({ initialQuery = '' }) {
  const [query, setQuery] = useState(initialQuery)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [suggestions, setSuggestions] = useState([])
  const [showSug, setShowSug] = useState(false)
  const [watched, setWatched] = useState(false)

  async function runSearch(symbol) {
    if (!symbol) return
    setShowSug(false)
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
      setWatched(isWatched(data.symbol))
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

  // 入力に応じて候補を取得（オートコンプリート、軽くデバウンス）
  useEffect(() => {
    const q = query.trim()
    if (q.length < 1) {
      setSuggestions([])
      return
    }
    const id = setTimeout(() => {
      fetch(`${API_BASE}/suggest?q=${encodeURIComponent(q)}`)
        .then((r) => r.json())
        .then((d) => setSuggestions(d.results || []))
        .catch(() => setSuggestions([]))
    }, 180)
    return () => clearTimeout(id)
  }, [query])

  function handleSearch(e) {
    e.preventDefault()
    runSearch(query.trim())
  }

  function pickSuggestion(s) {
    setQuery(s.name)
    setShowSug(false)
    runSearch(s.symbol)
  }

  function onWatch() {
    if (!result) return
    toggleWatch({ symbol: result.symbol, name: result.name || result.symbol })
    setWatched(isWatched(result.symbol))
  }

  const up = result && result.change != null && result.change >= 0

  return (
    <div>
      <form className="field" onSubmit={handleSearch} autoComplete="off">
        <div className="search-box">
          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setShowSug(true)
            }}
            onFocus={() => setShowSug(true)}
            onBlur={() => setTimeout(() => setShowSug(false), 150)}
            placeholder="会社名・コードでもOK（例: 理研計器 / 7203 / apple）"
          />
          {showSug && suggestions.length > 0 && (
            <ul className="suggest">
              {suggestions.map((s) => (
                <li key={s.symbol} onMouseDown={() => pickSuggestion(s)}>
                  <span className="sug-name">{s.name}</span>
                  <span className="sug-sym">{s.symbol}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
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
            <div className="detail-title">
              <h2 className="detail-name">{result.name || result.symbol}</h2>
              <button
                className={`watch-btn ${watched ? 'on' : ''}`}
                onClick={onWatch}
                title={watched ? 'ウォッチ解除' : 'ウォッチに追加'}
              >
                {watched ? '★ ウォッチ中' : '☆ ウォッチ'}
              </button>
            </div>
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

          {/* チャート（時間レンジ切替） */}
          <Chart symbol={result.symbol} currency={result.currency} />

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

          {/* 配当・株主優待 */}
          {(result.dividend || result.yutai_url) && (
            <div className="panel">
              <h3 className="panel-title">配当・株主優待</h3>
              {result.dividend && result.dividend.rate != null ? (
                <>
                  <div className="stat-grid">
                    <div className="stat">
                      <span className="stat-label">配当利回り</span>
                      <span className="stat-value pos">
                        {result.dividend.yield_pct != null
                          ? `${result.dividend.yield_pct}%`
                          : '—'}
                      </span>
                    </div>
                    <div className="stat">
                      <span className="stat-label">1株あたり年間配当</span>
                      <span className="stat-value">
                        {result.dividend.rate.toLocaleString()} {result.currency}
                      </span>
                    </div>
                    {/* 1単元で年間いくら（日本株は単元=100株なので分かりやすい） */}
                    {result.dividend.unit_shares === 100 &&
                      result.dividend.annual_per_unit != null && (
                        <div className="stat">
                          <span className="stat-label">1単元(100株)で年間</span>
                          <span className="stat-value pos">
                            {result.dividend.annual_per_unit.toLocaleString()} {result.currency}
                          </span>
                        </div>
                      )}
                    <div className="stat">
                      <span className="stat-label">配当性向</span>
                      <span className="stat-value sm">
                        {result.dividend.payout_pct != null
                          ? `${result.dividend.payout_pct}%`
                          : '—'}
                      </span>
                    </div>
                  </div>
                  {result.dividend.ex_date && (
                    <p className="note">次回の権利確定日（目安）: {result.dividend.ex_date}</p>
                  )}
                </>
              ) : (
                <p className="note">配当データはありません（無配のか、取得できない銘柄です）。</p>
              )}

              {/* 株主優待は外部サイトで確認（日本株のみ） */}
              {result.yutai_url && (
                <a
                  className="yutai-link"
                  href={result.yutai_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  株主優待・配当の詳細を見る（Yahoo!ファイナンス）↗
                </a>
              )}
            </div>
          )}

          {/* どんな企業か */}
          {result.summary && (
            <div className="panel">
              <h3 className="panel-title">どんな企業？</h3>
              <Summary text={result.summary} />
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

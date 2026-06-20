import { useState } from 'react'
import { API_BASE, formatSigned } from './utils.js'

// 予算のプリセット（円）
const PRESETS = [100000, 300000, 500000, 1000000]

// 買い時ラベル → 色分け用のクラス名
function timingClass(label) {
  if (label === '買い時') return 'good'
  if (label === 'やや買い時') return 'ok'
  if (label === '高値圏') return 'bad'
  return 'neutral'
}

// 購入可能数の表示（日本株は単元、それ以外は株）
function buyUnit(s) {
  return s.units === 100
    ? `${s.affordable}単元(${s.affordable * 100}株)`
    : `${s.affordable}株`
}

// 予算を入れると、買えるおすすめ銘柄を業界ごとに表示する画面
export default function Recommend() {
  const [budget, setBudget] = useState(500000)
  const [stocks, setStocks] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function fetchRecommend(b) {
    setLoading(true)
    setError('')
    setStocks(null)
    try {
      const res = await fetch(`${API_BASE}/recommendations?budget=${b}`)
      if (!res.ok) throw new Error('おすすめ銘柄を取得できませんでした。')
      const data = await res.json()
      setStocks(data.stocks)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function handleSubmit(e) {
    e.preventDefault()
    fetchRecommend(budget)
  }

  // 業界(セクター)ごとにグループ化する
  const groups = {}
  if (stocks) {
    for (const s of stocks) {
      ;(groups[s.sector] ??= []).push(s)
    }
  }

  return (
    <div>
      {/* 予算入力欄 ＋ ボタン */}
      <form className="search" onSubmit={handleSubmit}>
        <input
          type="number"
          value={budget}
          min="0"
          step="10000"
          onChange={(e) => setBudget(Number(e.target.value))}
        />
        <button type="submit" disabled={loading}>
          {loading ? '集計中...' : 'おすすめを見る'}
        </button>
      </form>

      {/* 予算のクイック選択 */}
      <div className="presets">
        {PRESETS.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => {
              setBudget(p)
              fetchRecommend(p)
            }}
          >
            {(p / 10000).toLocaleString()}万円
          </button>
        ))}
      </div>

      {error && <p className="error">{error}</p>}
      {loading && (
        <p className="hint">銘柄を集計しています（数十秒かかることがあります）…</p>
      )}

      {stocks && stocks.length === 0 && (
        <p className="hint">予算内で購入できる銘柄が見つかりませんでした。</p>
      )}

      {/* 業界ごとにおすすめ銘柄を表示 */}
      {stocks &&
        Object.entries(groups).map(([sector, list]) => (
          <div key={sector} className="sector">
            <h3 className="sector-title">{sector}</h3>
            {list.map((s) => (
              <div key={s.ticker} className="rec-card">
                <div className="rec-head">
                  <span className="rec-name">{s.name}</span>
                  {/* 買い時バッジ */}
                  <span className={`timing timing-${timingClass(s.timing_label)}`}>
                    {s.timing_label}
                  </span>
                </div>
                <div className="rec-row">
                  <span>最低購入額</span>
                  <span>
                    {Math.round(s.min_cost).toLocaleString()}円（{buyUnit(s)}）
                  </span>
                </div>
                <div className="rec-row">
                  <span>アナリスト評価</span>
                  <span>
                    {s.is_buy ? '★ ' : ''}
                    {s.rec_label}
                    {s.upside != null &&
                      `（上振れ ${formatSigned(Math.round(s.upside))}%）`}
                  </span>
                </div>
                <div className="rec-reason">{s.timing_reason}</div>
              </div>
            ))}
          </div>
        ))}

      {stocks && stocks.length > 0 && (
        <p className="disclaimer">
          ※ Yahoo Finance のデータに基づく参考情報です。投資はご自身の判断と責任で行ってください。
        </p>
      )}
    </div>
  )
}

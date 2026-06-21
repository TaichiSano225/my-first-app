import { useEffect, useState } from 'react'
import { API_BASE, formatSigned, timingClass } from './utils.js'
import RangeBar from './RangeBar.jsx'

// 予算のクイック選択（円）
const PRESETS = [100000, 300000, 500000, 1000000]

// 「すべての業界」を表す擬似的な選択肢
const ALL = 'すべての業界'

// 地域の選択肢
const REGIONS = [
  { key: 'jp', label: '国内（日本株）' },
  { key: 'us', label: '海外（米国株）' },
  { key: 'all', label: 'すべて' },
]
const REGION_LABEL = { jp: '国内', us: '海外', all: '国内＋海外' }

// 購入可能数の表示（日本株は単元、それ以外は株）
function buyUnit(s) {
  return s.units === 100
    ? `${s.affordable}単元(${s.affordable * 100}株)`
    : `${s.affordable}株`
}

// 業界を選び、その中で予算内・買い時順のおすすめ銘柄を表示する画面
export default function Recommend() {
  const [sectors, setSectors] = useState([])
  const [themes, setThemes] = useState([])
  const [sector, setSector] = useState(ALL)
  const [region, setRegion] = useState('jp')
  const [budget, setBudget] = useState(300000)
  const [stocks, setStocks] = useState(null)
  const [shownRegion, setShownRegion] = useState('jp')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // 起動時に業界・テーマの一覧を取得してセレクトに入れる
  useEffect(() => {
    fetch(`${API_BASE}/sectors`)
      .then((res) => res.json())
      .then((data) => {
        setSectors(data.sectors || [])
        setThemes(data.themes || [])
      })
      .catch(() => setError('業界一覧を取得できませんでした。'))
  }, [])

  async function fetchRecommend(targetSector, targetBudget, targetRegion) {
    setLoading(true)
    setError('')
    setStocks(null)
    try {
      // 「すべての業界」のときは sector を付けない（＝全業界が対象）
      const sectorParam =
        targetSector && targetSector !== ALL
          ? `sector=${encodeURIComponent(targetSector)}&`
          : ''
      const res = await fetch(
        `${API_BASE}/recommendations?${sectorParam}budget=${targetBudget}&region=${targetRegion}`,
      )
      if (!res.ok) throw new Error('おすすめ銘柄を取得できませんでした。')
      const data = await res.json()
      setStocks(data.stocks)
      setShownRegion(targetRegion)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function handleSubmit(e) {
    e.preventDefault()
    fetchRecommend(sector, budget, region)
  }

  return (
    <div>
      <form className="rec-form" onSubmit={handleSubmit}>
        <label className="select-wrap">
          <span className="select-label">地域</span>
          <select value={region} onChange={(e) => setRegion(e.target.value)}>
            {REGIONS.map((r) => (
              <option key={r.key} value={r.key}>
                {r.label}
              </option>
            ))}
          </select>
        </label>

        <label className="select-wrap">
          <span className="select-label">業界・テーマ</span>
          <select value={sector} onChange={(e) => setSector(e.target.value)}>
            <option value={ALL}>{ALL}</option>
            <optgroup label="テーマ">
              {themes.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </optgroup>
            <optgroup label="業界">
              {sectors.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </optgroup>
          </select>
        </label>

        <label className="select-wrap">
          <span className="select-label">予算（円）</span>
          <input
            type="number"
            value={budget}
            min="0"
            step="10000"
            onChange={(e) => setBudget(Number(e.target.value))}
          />
        </label>

        <button type="submit" disabled={loading || !sector}>
          {loading ? '集計中…' : 'おすすめを見る'}
        </button>
      </form>

      {/* 予算クイック選択 */}
      <div className="presets">
        {PRESETS.map((p) => (
          <button
            key={p}
            type="button"
            className={budget === p ? 'active' : ''}
            onClick={() => {
              setBudget(p)
              fetchRecommend(sector, p, region)
            }}
          >
            {(p / 10000).toLocaleString()}万円
          </button>
        ))}
      </div>

      {error && <p className="error">{error}</p>}
      {loading && <p className="hint">買い時順に集計しています…</p>}

      {stocks && stocks.length === 0 && (
        <p className="hint">この予算で買える銘柄が見つかりませんでした。予算を増やしてみてください。</p>
      )}

      {stocks && stocks.length > 0 && (
        <>
          <p className="rec-count">
            {REGION_LABEL[shownRegion]}・{sector}：買い時順に{' '}
            <strong>{stocks.length}</strong> 銘柄
          </p>
          <div className="rec-list">
            {stocks.map((s, i) => (
              <div key={s.ticker} className="rec-card">
                <div className="rec-rank">{i + 1}</div>
                <div className="rec-main">
                  <div className="rec-head">
                    <div>
                      {/* 企業名をクリックすると別タブで詳細（どんな企業か等）を開く */}
                      <a
                        className="rec-name rec-link"
                        href={`/?q=${encodeURIComponent(s.ticker)}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {s.name}
                      </a>
                      <span className="rec-ticker">{s.ticker}</span>
                      {s.sector && <span className="rec-sector">{s.sector}</span>}
                    </div>
                    <span className={`timing timing-${timingClass(s.timing_label)}`}>
                      {s.timing_label}
                    </span>
                  </div>

                  <div className="rec-metrics">
                    <span>
                      最低 <strong>{s.min_cost.toLocaleString()}円</strong>（{buyUnit(s)}）
                    </span>
                    {s.change_pct != null && (
                      <span className={s.change_pct >= 0 ? 'pos' : 'neg'}>
                        前日比 {formatSigned(s.change_pct)}%
                      </span>
                    )}
                  </div>

                  <RangeBar pct={s.range_pct} />
                  {/* クリックで買い時の根拠（文章）を開閉 */}
                  <details className="rec-why">
                    <summary>{s.timing_reason}</summary>
                    <p>{s.timing_detail}</p>
                  </details>
                </div>
              </div>
            ))}
          </div>
          <p className="disclaimer">
            ※ 株価データに基づく「買い時」の目安です（割安・移動平均からの簡易判定）。
            Yahoo Finance のデータに基づく参考情報であり、投資助言ではありません。
          </p>
        </>
      )}
    </div>
  )
}

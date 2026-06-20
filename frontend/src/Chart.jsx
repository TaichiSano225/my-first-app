import { useEffect, useState } from 'react'
import { API_BASE } from './utils.js'

// 選べる時間レンジ
const RANGES = [
  { key: '1mo', label: '1ヶ月' },
  { key: '3mo', label: '3ヶ月' },
  { key: '6mo', label: '6ヶ月' },
  { key: '1y', label: '1年' },
  { key: '5y', label: '5年' },
  { key: 'max', label: '全期間' },
]

// SVG で描く折れ線チャート（外部ライブラリ不要）
function LineChart({ points, currency }) {
  const W = 620
  const H = 240
  const pad = { l: 6, r: 6, t: 14, b: 6 }
  const cs = points.map((p) => p.c)
  const min = Math.min(...cs)
  const max = Math.max(...cs)
  const n = points.length
  const innerW = W - pad.l - pad.r
  const innerH = H - pad.t - pad.b

  const x = (i) => pad.l + (n === 1 ? 0 : (i / (n - 1)) * innerW)
  const y = (c) => pad.t + (max === min ? innerH / 2 : (1 - (c - min) / (max - min)) * innerH)

  const line = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(p.c).toFixed(1)}`)
    .join(' ')
  const area =
    `${line} L${x(n - 1).toFixed(1)},${(pad.t + innerH).toFixed(1)} ` +
    `L${x(0).toFixed(1)},${(pad.t + innerH).toFixed(1)} Z`

  const first = cs[0]
  const last = cs[n - 1]
  const up = last >= first
  const chg = first ? ((last - first) / first) * 100 : 0
  const color = up ? '#34d399' : '#fb7185'
  const gid = up ? 'grad-up' : 'grad-dn'

  return (
    <div>
      <div className="chart-head">
        <span className="chart-last">
          {last.toLocaleString()} <small>{currency}</small>
        </span>
        <span className={up ? 'pos' : 'neg'}>
          {(chg >= 0 ? '+' : '') + chg.toFixed(1)}%（期間）
        </span>
      </div>
      <svg className="chart-svg" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="価格チャート">
        <defs>
          <linearGradient id={gid} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.28" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={area} fill={`url(#${gid})`} />
        <path d={line} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
      </svg>
      <div className="chart-axis">
        <span>{points[0].t}</span>
        <span>
          高 {max.toLocaleString()} / 安 {min.toLocaleString()}
        </span>
        <span>{points[n - 1].t}</span>
      </div>
    </div>
  )
}

// レンジ切替つきのチャートパネル
export default function Chart({ symbol, currency }) {
  const [range, setRange] = useState('6mo')
  const [points, setPoints] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let alive = true
    setLoading(true)
    fetch(`${API_BASE}/history/${encodeURIComponent(symbol)}?range=${range}`)
      .then((r) => r.json())
      .then((d) => {
        if (alive) setPoints(d.points || [])
      })
      .catch(() => {
        if (alive) setPoints([])
      })
      .finally(() => {
        if (alive) setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [symbol, range])

  return (
    <div className="panel">
      <h3 className="panel-title">チャート</h3>
      <div className="range-tabs">
        {RANGES.map((r) => (
          <button
            key={r.key}
            className={range === r.key ? 'active' : ''}
            onClick={() => setRange(r.key)}
          >
            {r.label}
          </button>
        ))}
      </div>
      {loading && <p className="hint">読み込み中…</p>}
      {!loading && points && points.length > 1 && (
        <LineChart points={points} currency={currency} />
      )}
      {!loading && points && points.length <= 1 && (
        <p className="note">この期間のデータがありません。</p>
      )}
    </div>
  )
}

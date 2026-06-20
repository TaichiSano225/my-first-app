import { useEffect, useState } from 'react'
import { API_BASE } from './utils.js'

// 主要指数・為替の概況バー（トップに表示）
export default function MarketBar() {
  const [market, setMarket] = useState([])

  useEffect(() => {
    fetch(`${API_BASE}/market`)
      .then((r) => r.json())
      .then((d) => setMarket(d.market || []))
      .catch(() => {})
  }, [])

  if (!market.length) return null

  return (
    <div className="market-bar">
      {market.map((m) => (
        <div className="mkt" key={m.label}>
          <span className="mkt-label">{m.label}</span>
          <span className="mkt-price">{m.price.toLocaleString()}</span>
          {m.change_pct != null && (
            <span className={`mkt-chg ${m.change_pct >= 0 ? 'pos' : 'neg'}`}>
              {(m.change_pct >= 0 ? '+' : '') + m.change_pct}%
            </span>
          )}
        </div>
      ))}
    </div>
  )
}

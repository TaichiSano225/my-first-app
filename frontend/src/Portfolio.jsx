import { useEffect, useMemo, useState } from 'react'
import { API_BASE, formatSigned } from './utils.js'
import {
  getWatchlist,
  removeWatch,
  getHoldings,
  addHolding,
  removeHolding,
} from './store.js'

const yen = (n) => Math.round(n).toLocaleString() + '円'

export default function Portfolio() {
  const [watch, setWatch] = useState(getWatchlist())
  const [holdings, setHoldings] = useState(getHoldings())
  const [quotes, setQuotes] = useState({}) // symbol -> quote
  const [form, setForm] = useState({ symbol: '', name: '', shares: '', cost: '' })

  // ウォッチ＋保有の全シンボルをまとめて取得
  const symbols = useMemo(
    () =>
      Array.from(
        new Set([...watch.map((w) => w.symbol), ...holdings.map((h) => h.symbol)]),
      ),
    [watch, holdings],
  )
  const symbolsKey = symbols.join(',')

  useEffect(() => {
    if (!symbolsKey) {
      setQuotes({})
      return
    }
    fetch(`${API_BASE}/quotes?symbols=${encodeURIComponent(symbolsKey)}&dividend=1`)
      .then((r) => r.json())
      .then((d) => {
        const map = {}
        ;(d.quotes || []).forEach((q) => {
          map[q.symbol] = q
        })
        setQuotes(map)
      })
      .catch(() => {})
  }, [symbolsKey])

  // ポートフォリオ集計（すべて円換算）
  const totals = useMemo(() => {
    let value = 0
    let cost = 0
    let dividend = 0
    let ok = false
    for (const h of holdings) {
      const q = quotes[h.symbol]
      if (!q || q.price == null) continue
      ok = true
      const ratio = q.price ? q.price_jpy / q.price : 1 // 通貨→円の係数
      value += h.shares * q.price_jpy
      cost += h.shares * h.cost * ratio
      dividend += h.shares * (q.dividend_rate_jpy || 0)
    }
    const pl = value - cost
    const plPct = cost > 0 ? (pl / cost) * 100 : null
    const yieldPct = value > 0 ? (dividend / value) * 100 : null
    return { value, cost, pl, plPct, dividend, yieldPct, ok }
  }, [holdings, quotes])

  function handleAdd(e) {
    e.preventDefault()
    const symbol = form.symbol.trim()
    const shares = Number(form.shares)
    const cost = Number(form.cost)
    if (!symbol || !shares || shares <= 0) return
    setHoldings(addHolding({ symbol, name: form.name || symbol, shares, cost: cost || 0 }))
    setForm({ symbol: '', name: '', shares: '', cost: '' })
  }

  const link = (s) => `/?q=${encodeURIComponent(s)}`

  return (
    <div>
      {/* ===== ウォッチリスト ===== */}
      <h3 className="section-title">ウォッチリスト</h3>
      {watch.length === 0 ? (
        <p className="hint">
          銘柄検索の画面で「★ウォッチ」を押すと、ここに追加されます。
        </p>
      ) : (
        <div className="wl-list">
          {watch.map((w) => {
            const q = quotes[w.symbol]
            return (
              <div className="wl-row" key={w.symbol}>
                <a className="wl-name rec-link" href={link(w.symbol)} target="_blank" rel="noreferrer">
                  {w.name}
                </a>
                <span className="wl-price">
                  {q && q.price != null ? q.price.toLocaleString() : '—'}
                </span>
                <span className={q && q.change_pct != null ? (q.change_pct >= 0 ? 'pos' : 'neg') : ''}>
                  {q && q.change_pct != null ? `${formatSigned(q.change_pct)}%` : ''}
                </span>
                <button
                  className="icon-btn"
                  title="保有に追加"
                  onClick={() => setForm({ ...form, symbol: w.symbol, name: w.name })}
                >
                  ＋
                </button>
                <button
                  className="icon-btn"
                  title="削除"
                  onClick={() => setWatch(removeWatch(w.symbol))}
                >
                  ×
                </button>
              </div>
            )
          })}
        </div>
      )}

      {/* ===== ポートフォリオ ===== */}
      <h3 className="section-title" style={{ marginTop: '28px' }}>
        ポートフォリオ
      </h3>

      {/* 集計サマリー */}
      {totals.ok && (
        <div className="pf-summary">
          <div className="stat">
            <span className="stat-label">評価額合計</span>
            <span className="stat-value">{yen(totals.value)}</span>
          </div>
          <div className="stat">
            <span className="stat-label">損益</span>
            <span className={`stat-value ${totals.pl >= 0 ? 'pos' : 'neg'}`}>
              {(totals.pl >= 0 ? '+' : '') + yen(totals.pl)}
              {totals.plPct != null && ` (${formatSigned(Math.round(totals.plPct * 10) / 10)}%)`}
            </span>
          </div>
          <div className="stat">
            <span className="stat-label">年間配当合計（税引前）</span>
            <span className="stat-value pos">
              {yen(totals.dividend)}
              {totals.yieldPct != null && ` (${(Math.round(totals.yieldPct * 10) / 10)}%)`}
            </span>
          </div>
        </div>
      )}

      {/* 保有銘柄リスト */}
      {holdings.length > 0 && (
        <div className="pf-list">
          {holdings.map((h, i) => {
            const q = quotes[h.symbol]
            const valJpy = q && q.price != null ? h.shares * q.price_jpy : null
            const ratio = q && q.price ? q.price_jpy / q.price : 1
            const plJpy = q && q.price != null ? h.shares * (q.price - h.cost) * ratio : null
            return (
              <div className="pf-row" key={i}>
                <div className="pf-main">
                  <a className="rec-link" href={link(h.symbol)} target="_blank" rel="noreferrer">
                    {h.name}
                  </a>
                  <span className="pf-sub">
                    {h.shares.toLocaleString()}株 / 取得 {h.cost.toLocaleString()}
                    {q ? ` ${q.currency}` : ''}
                  </span>
                </div>
                <div className="pf-vals">
                  <span>{valJpy != null ? yen(valJpy) : '—'}</span>
                  {plJpy != null && (
                    <span className={plJpy >= 0 ? 'pos' : 'neg'}>
                      {(plJpy >= 0 ? '+' : '') + yen(plJpy)}
                    </span>
                  )}
                </div>
                <button className="icon-btn" title="削除" onClick={() => setHoldings(removeHolding(i))}>
                  ×
                </button>
              </div>
            )
          })}
        </div>
      )}

      {/* 保有を追加するフォーム */}
      <form className="pf-form" onSubmit={handleAdd}>
        <input
          type="text"
          placeholder="銘柄コード/ティッカー（例: 7203.T）"
          value={form.symbol}
          onChange={(e) => setForm({ ...form, symbol: e.target.value, name: '' })}
        />
        <input
          type="number"
          placeholder="株数"
          min="0"
          value={form.shares}
          onChange={(e) => setForm({ ...form, shares: e.target.value })}
        />
        <input
          type="number"
          placeholder="取得単価"
          min="0"
          step="0.01"
          value={form.cost}
          onChange={(e) => setForm({ ...form, cost: e.target.value })}
        />
        <button type="submit">追加</button>
      </form>
      <p className="note">
        ※ 合計はすべて円換算（外国株は現在のレートで換算）。配当は税引前の概算です。データはこの端末にのみ保存されます。
      </p>
    </div>
  )
}

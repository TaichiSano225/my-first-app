import { useEffect, useMemo, useRef, useState } from 'react'
import { API_BASE, formatSigned } from './utils.js'
import {
  getWatchlist,
  removeWatch,
  getHoldings,
  addHolding,
  removeHolding,
  exportBackup,
  importBackup,
} from './store.js'
import SymbolInput from './SymbolInput.jsx'

const yen = (n) => Math.round(n).toLocaleString() + '円'

export default function Portfolio({ onOpen }) {
  const [watch, setWatch] = useState(getWatchlist())
  const [holdings, setHoldings] = useState(getHoldings())
  const [quotes, setQuotes] = useState({}) // symbol -> quote
  const [form, setForm] = useState({ symbol: '', name: '', shares: '', cost: '' })
  // 銘柄欄の表示用（社名で選んでも、送信するのはティッカー）
  const [symbolText, setSymbolText] = useState('')
  const [backupMessage, setBackupMessage] = useState('')
  const fileInputRef = useRef(null)

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
    // 候補から選んでいなければ、入力された文字をそのままティッカーとして扱う
    const symbol = (form.symbol || symbolText).trim()
    const shares = Number(form.shares)
    const cost = Number(form.cost)
    if (!symbol || !shares || shares <= 0) return
    setHoldings(addHolding({ symbol, name: form.name || symbol, shares, cost: cost || 0 }))
    setForm({ symbol: '', name: '', shares: '', cost: '' })
    setSymbolText('')
  }

  // 保有に追加する銘柄を、ウォッチリストの「＋」やサジェストから流し込む
  function fillSymbol({ symbol, name }) {
    setForm((f) => ({ ...f, symbol, name }))
    setSymbolText(name || symbol)
  }

  // --- バックアップ（この端末にしか残らないデータを守る） ---
  function handleExport() {
    const blob = new Blob([JSON.stringify(exportBackup(), null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'stock-pulse-backup.json'
    a.click()
    URL.revokeObjectURL(url)
    setBackupMessage('バックアップを保存しました。')
  }

  async function handleImport(e) {
    const file = e.target.files?.[0]
    e.target.value = '' // 同じファイルを選び直せるようにする
    if (!file) return
    try {
      const counts = importBackup(JSON.parse(await file.text()))
      setWatch(getWatchlist())
      setHoldings(getHoldings())
      setBackupMessage(
        `復元しました（ウォッチ ${counts.watchlist} 件・保有 ${counts.holdings} 件）。`,
      )
    } catch (err) {
      setBackupMessage(`復元できませんでした: ${err.message}`)
    }
  }

  // 銘柄名クリック：この画面のまま検索タブで詳細を開く（href は別タブ用に残す）
  const link = (s) => `/?q=${encodeURIComponent(s)}`

  function handleOpen(e, symbol) {
    if (!onOpen) return
    e.preventDefault()
    onOpen(symbol)
  }

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
                <a
                  className="wl-name rec-link"
                  href={link(w.symbol)}
                  target="_blank"
                  rel="noreferrer"
                  onClick={(e) => handleOpen(e, w.symbol)}
                >
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
                  onClick={() => fillSymbol({ symbol: w.symbol, name: w.name })}
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
                  <a
                    className="rec-link"
                    href={link(h.symbol)}
                    target="_blank"
                    rel="noreferrer"
                    onClick={(e) => handleOpen(e, h.symbol)}
                  >
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

      {/* 保有を追加するフォーム（社名でも探せる） */}
      <form className="pf-form" onSubmit={handleAdd} autoComplete="off">
        <div className="pf-symbol">
          <SymbolInput
            value={symbolText}
            onChange={(text) => {
              setSymbolText(text)
              // 手入力に切り替えたら、選択済みの銘柄をいったん忘れる
              setForm((f) => ({ ...f, symbol: '', name: '' }))
            }}
            onPick={(s) => fillSymbol({ symbol: s.symbol, name: s.name })}
            placeholder="社名・コードで検索（例: トヨタ / 7203 / AAPL）"
            clearable
          />
        </div>
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
      {form.symbol && (
        <p className="note">選択中: {form.name}（{form.symbol}）</p>
      )}

      {/* ===== バックアップ ===== */}
      <div className="backup">
        <span className="backup-label">バックアップ</span>
        <button type="button" className="ghost-btn" onClick={handleExport}>
          ファイルに保存
        </button>
        <button type="button" className="ghost-btn" onClick={() => fileInputRef.current?.click()}>
          ファイルから復元
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="application/json,.json"
          hidden
          onChange={handleImport}
        />
      </div>
      {backupMessage && <p className="note">{backupMessage}</p>}

      <p className="note">
        ※ 合計はすべて円換算（外国株は現在のレートで換算）。配当は税引前の概算です。
        データはこの端末のブラウザにのみ保存されるため、機種変更や履歴の削除で消えます。
        大事な内容は「ファイルに保存」でバックアップしてください。
      </p>
    </div>
  )
}

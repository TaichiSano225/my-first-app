import { useEffect, useState } from 'react'
import StockSearch from './StockSearch.jsx'
import Recommend from './Recommend.jsx'
import Portfolio from './Portfolio.jsx'
import MarketBar from './MarketBar.jsx'
import ThemeToggle from './ThemeToggle.jsx'

// URL の ?q=... を読む（外部リンクや別タブで企業詳細を開くときに使う）
const initialQuery = new URLSearchParams(window.location.search).get('q') || ''

const TAB_KEY = 'sp_tab'
const TABS = [
  { key: 'search', label: '銘柄を検索' },
  { key: 'recommend', label: '予算でおすすめ' },
  { key: 'mylist', label: 'マイリスト' },
]

// 前回開いていたタブを復元する（?q= 付きで開かれたときは検索タブ）
function initialTab() {
  if (initialQuery) return 'search'
  const saved = localStorage.getItem(TAB_KEY)
  return TABS.some((t) => t.key === saved) ? saved : 'search'
}

export default function App() {
  const [tab, setTab] = useState(initialTab)
  // マイリスト・おすすめから「この銘柄を開く」と指示された内容。
  // 同じ銘柄を続けて開いても検知できるよう seq を持たせる。
  const [openRequest, setOpenRequest] = useState(null)

  // 次に開いたときも同じタブから始められるように覚えておく
  useEffect(() => {
    localStorage.setItem(TAB_KEY, tab)
  }, [tab])

  // 別タブを開かず、この画面のまま検索タブで銘柄の詳細を表示する
  function openSymbol(symbol) {
    setOpenRequest((prev) => ({ symbol, seq: (prev?.seq || 0) + 1 }))
    setTab('search')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <div className="container">
      <header className="brand">
        <ThemeToggle />
        <h1>Stock Pulse</h1>
        <p>株価・買い時・おすすめ銘柄をひと目で</p>
      </header>

      {/* マーケット概況 */}
      <MarketBar />

      {/* タブ切り替え */}
      <div className="tabs">
        {TABS.map((t) => (
          <button
            key={t.key}
            className={tab === t.key ? 'active' : ''}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* 選択中のタブに応じて画面を切り替える */}
      {tab === 'search' && <StockSearch initialQuery={initialQuery} openRequest={openRequest} />}
      {tab === 'recommend' && <Recommend onOpen={openSymbol} />}
      {tab === 'mylist' && <Portfolio onOpen={openSymbol} />}
    </div>
  )
}

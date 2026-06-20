import { useState } from 'react'
import StockSearch from './StockSearch.jsx'
import Recommend from './Recommend.jsx'
import Portfolio from './Portfolio.jsx'
import MarketBar from './MarketBar.jsx'

// URL の ?q=... を読む（別タブで企業詳細を開くときに使う）
const initialQuery = new URLSearchParams(window.location.search).get('q') || ''

export default function App() {
  // タブの状態（検索タブを初期表示。?q= 付きで開かれた場合も検索を表示する）
  const [tab, setTab] = useState('search')

  return (
    <div className="container">
      <header className="brand">
        <h1>Stock Pulse</h1>
        <p>株価・買い時・おすすめ銘柄をひと目で</p>
      </header>

      {/* マーケット概況 */}
      <MarketBar />

      {/* タブ切り替え */}
      <div className="tabs">
        <button className={tab === 'search' ? 'active' : ''} onClick={() => setTab('search')}>
          銘柄を検索
        </button>
        <button className={tab === 'recommend' ? 'active' : ''} onClick={() => setTab('recommend')}>
          予算でおすすめ
        </button>
        <button className={tab === 'mylist' ? 'active' : ''} onClick={() => setTab('mylist')}>
          マイリスト
        </button>
      </div>

      {/* 選択中のタブに応じて画面を切り替える */}
      {tab === 'search' && <StockSearch initialQuery={initialQuery} />}
      {tab === 'recommend' && <Recommend />}
      {tab === 'mylist' && <Portfolio />}
    </div>
  )
}

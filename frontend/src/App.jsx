import { useState } from 'react'
import StockSearch from './StockSearch.jsx'
import Recommend from './Recommend.jsx'

export default function App() {
  // 表示中のタブ ('search' = 銘柄検索, 'recommend' = おすすめ)
  const [tab, setTab] = useState('search')

  return (
    <div className="container">
      <h1>株価チェッカー</h1>

      {/* タブ切り替え */}
      <div className="tabs">
        <button
          className={tab === 'search' ? 'active' : ''}
          onClick={() => setTab('search')}
        >
          銘柄を検索
        </button>
        <button
          className={tab === 'recommend' ? 'active' : ''}
          onClick={() => setTab('recommend')}
        >
          予算でおすすめ
        </button>
      </div>

      {/* 選択中のタブに応じて画面を切り替える */}
      {tab === 'search' ? <StockSearch /> : <Recommend />}
    </div>
  )
}

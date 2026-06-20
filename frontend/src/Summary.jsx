import { useState } from 'react'

// 企業概要を読みやすく表示する。
// 長い文章は「最初の2文」だけ見せ、「もっと見る」で残りを展開する。
export default function Summary({ text }) {
  const [open, setOpen] = useState(false)

  // 「。」で文に分割
  const sentences = text
    .split('。')
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s) => s + '。')

  const head = sentences.slice(0, 2).join('')
  const rest = sentences.slice(2).join('')

  return (
    <div>
      <p className="summary">{head}</p>
      {rest && open && <p className="summary">{rest}</p>}
      {rest && (
        <button className="more-btn" onClick={() => setOpen(!open)}>
          {open ? '閉じる' : 'もっと見る'}
        </button>
      )}
    </div>
  )
}

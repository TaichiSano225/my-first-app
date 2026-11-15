import { useEffect, useRef, useState } from 'react'
import { API_BASE } from './utils.js'

// 候補を取りに行くまでの待ち時間（打ち終わってから叩くため）
const DEBOUNCE_MS = 180

/**
 * 社名・証券コードのオートコンプリート付き入力欄。
 * 銘柄検索の画面と、マイリストの「保有を追加」フォームで共用する。
 *
 * マウスだけでなくキーボードでも候補を選べる。
 *   ↑ ↓ : 候補を移動 / Enter : 選択（未選択なら通常の送信）/ Esc : 候補を閉じる
 */
export default function SymbolInput({
  value,
  onChange,
  onPick,
  placeholder,
  clearable = false,
}) {
  const [suggestions, setSuggestions] = useState([])
  const [open, setOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(-1)
  const inputRef = useRef(null)
  const listRef = useRef(null)
  // 候補を選んだ直後は、入力欄が書き換わっても候補を取り直さない
  const skipNextFetch = useRef(false)

  // 入力に応じて候補を取得する（軽くデバウンス）
  useEffect(() => {
    if (skipNextFetch.current) {
      skipNextFetch.current = false
      return
    }
    const q = value.trim()
    if (!q) {
      setSuggestions([])
      setActiveIndex(-1)
      return
    }
    const timer = setTimeout(() => {
      fetch(`${API_BASE}/suggest?q=${encodeURIComponent(q)}`)
        .then((res) => res.json())
        .then((data) => {
          setSuggestions(data.results || [])
          setActiveIndex(-1)
        })
        .catch(() => setSuggestions([]))
    }, DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [value])

  // キーボードで移動したとき、選択中の候補が見えるようにスクロールする
  useEffect(() => {
    if (activeIndex < 0 || !listRef.current) return
    listRef.current.children[activeIndex]?.scrollIntoView({ block: 'nearest' })
  }, [activeIndex])

  const visible = open && suggestions.length > 0

  function pick(suggestion) {
    skipNextFetch.current = true
    setOpen(false)
    setActiveIndex(-1)
    onPick(suggestion)
  }

  function handleKeyDown(e) {
    if (e.key === 'Escape') {
      setOpen(false)
      setActiveIndex(-1)
      return
    }
    if (e.key === 'Enter') {
      // 候補を選んでいるときだけ横取りする（未選択なら通常どおりフォーム送信）
      if (visible && activeIndex >= 0) {
        e.preventDefault()
        pick(suggestions[activeIndex])
      }
      return
    }
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return

    e.preventDefault()
    if (!visible) {
      setOpen(true)
      return
    }
    // 端まで来たら反対側へ回り込む（未選択 -1 からは、↓なら先頭・↑なら末尾へ）
    const last = suggestions.length - 1
    if (e.key === 'ArrowDown') setActiveIndex((i) => (i >= last ? 0 : i + 1))
    else setActiveIndex((i) => (i <= 0 ? last : i - 1))
  }

  function handleClear() {
    skipNextFetch.current = false
    onChange('')
    setSuggestions([])
    setActiveIndex(-1)
    inputRef.current?.focus()
  }

  return (
    <div className="search-box">
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => {
          onChange(e.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        // 候補のクリック（mousedown）を先に処理させるため、閉じるのを少し遅らせる
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        role="combobox"
        aria-expanded={visible}
        aria-autocomplete="list"
        aria-activedescendant={activeIndex >= 0 ? `sug-${activeIndex}` : undefined}
      />

      {clearable && value && (
        <button type="button" className="clear-btn" onClick={handleClear} title="入力を消す">
          ×
        </button>
      )}

      {visible && (
        <ul className="suggest" ref={listRef} role="listbox">
          {suggestions.map((s, i) => (
            <li
              key={s.symbol}
              id={`sug-${i}`}
              role="option"
              aria-selected={i === activeIndex}
              className={i === activeIndex ? 'active' : ''}
              onMouseDown={() => pick(s)}
              onMouseEnter={() => setActiveIndex(i)}
            >
              <span className="sug-name">{s.name}</span>
              <span className="sug-sym">{s.symbol}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

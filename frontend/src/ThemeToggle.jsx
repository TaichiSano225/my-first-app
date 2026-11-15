import { useEffect, useState } from 'react'
import { THEMES, applyTheme, getTheme, setTheme, watchSystemTheme } from './theme.js'

// 配色（自動／ダーク／ライト）を切り替えるボタン。押すたびに順番に切り替わる。
export default function ThemeToggle() {
  const [theme, setThemeState] = useState(getTheme)

  // 'auto' のときは、端末のダークモード設定の変化に追従する
  useEffect(() => {
    applyTheme(theme)
    if (theme !== 'auto') return
    return watchSystemTheme(() => applyTheme('auto'))
  }, [theme])

  function cycleTheme() {
    const next = THEMES[(THEMES.findIndex((t) => t.key === theme) + 1) % THEMES.length]
    setTheme(next.key)
    setThemeState(next.key)
  }

  const current = THEMES.find((t) => t.key === theme)

  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={cycleTheme}
      title={`配色: ${current.label}（クリックで切り替え）`}
      aria-label={`配色を切り替える。現在は${current.label}`}
    >
      <span aria-hidden="true">{current.icon}</span>
      <span className="theme-label">{current.label}</span>
    </button>
  )
}

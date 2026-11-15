// 画面の配色（ダーク／ライト）を切り替える。
// 'auto' は端末のシステム設定に追従する。選択は localStorage に保存する。
const TKEY = 'sp_theme'

// 切り替えボタンで順に回る選択肢
export const THEMES = [
  { key: 'auto', label: '自動', icon: '🖥' },
  { key: 'dark', label: 'ダーク', icon: '🌙' },
  { key: 'light', label: 'ライト', icon: '☀️' },
]

// ブラウザのアドレスバー色（PWA でも使われる）
const THEME_COLOR = { dark: '#070b16', light: '#f5f7fb' }

export function getTheme() {
  const saved = localStorage.getItem(TKEY)
  return THEMES.some((t) => t.key === saved) ? saved : 'auto'
}

function prefersDark() {
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
}

// 'auto' を実際の配色（dark / light）に解決する
export function resolveTheme(theme) {
  return theme === 'auto' ? (prefersDark() ? 'dark' : 'light') : theme
}

export function applyTheme(theme) {
  const resolved = resolveTheme(theme)
  document.documentElement.dataset.theme = resolved
  const meta = document.querySelector('meta[name="theme-color"]')
  if (meta) meta.setAttribute('content', THEME_COLOR[resolved])
  return resolved
}

export function setTheme(theme) {
  localStorage.setItem(TKEY, theme)
  return applyTheme(theme)
}

/**
 * システム設定の変更を監視する（'auto' のときだけ画面へ反映する）。
 * 戻り値は監視をやめる関数。
 */
export function watchSystemTheme(onChange) {
  if (!window.matchMedia) return () => {}
  const query = window.matchMedia('(prefers-color-scheme: dark)')
  const handler = () => onChange()
  query.addEventListener('change', handler)
  return () => query.removeEventListener('change', handler)
}

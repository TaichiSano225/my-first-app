// ウォッチリストとポートフォリオをブラウザ(localStorage)に保存する。
// ログイン不要だが、保存はその端末のブラウザ内のみ。
const WKEY = 'sp_watchlist'
const HKEY = 'sp_holdings'

function read(key) {
  try {
    return JSON.parse(localStorage.getItem(key)) || []
  } catch {
    return []
  }
}

function write(key, value) {
  localStorage.setItem(key, JSON.stringify(value))
}

// --- ウォッチリスト: [{symbol, name}] ---
export const getWatchlist = () => read(WKEY)

export function isWatched(symbol) {
  return read(WKEY).some((x) => x.symbol === symbol)
}

export function toggleWatch(item) {
  const list = read(WKEY)
  const i = list.findIndex((x) => x.symbol === item.symbol)
  if (i >= 0) list.splice(i, 1)
  else list.push({ symbol: item.symbol, name: item.name })
  write(WKEY, list)
  return list
}

export function removeWatch(symbol) {
  const list = read(WKEY).filter((x) => x.symbol !== symbol)
  write(WKEY, list)
  return list
}

// --- ポートフォリオ: [{symbol, name, shares, cost}] ---
export const getHoldings = () => read(HKEY)

export function addHolding(h) {
  const list = read(HKEY)
  list.push(h)
  write(HKEY, list)
  return list
}

export function removeHolding(index) {
  const list = read(HKEY)
  list.splice(index, 1)
  write(HKEY, list)
  return list
}

// ウォッチリスト・ポートフォリオ・検索履歴をブラウザ(localStorage)に保存する。
// ログイン不要だが、保存はその端末のブラウザ内のみ。
// 端末を変える／履歴を消すと失われるため、バックアップの書き出し・読み込みも用意する。
const WKEY = 'sp_watchlist'
const HKEY = 'sp_holdings'
const RKEY = 'sp_recent'

// 検索履歴として残す件数
const RECENT_MAX = 8

// バックアップファイルの形式バージョン（将来の互換判定用）
const BACKUP_VERSION = 1

function read(key) {
  try {
    const value = JSON.parse(localStorage.getItem(key))
    return Array.isArray(value) ? value : []
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

// --- 検索履歴（最近見た銘柄）: [{symbol, name}] 新しい順 ---
export const getRecent = () => read(RKEY)

export function pushRecent(item) {
  // 同じ銘柄は先頭に繰り上げたいので、いったん取り除いてから足す
  const list = read(RKEY).filter((x) => x.symbol !== item.symbol)
  list.unshift({ symbol: item.symbol, name: item.name || item.symbol })
  write(RKEY, list.slice(0, RECENT_MAX))
  return read(RKEY)
}

export function clearRecent() {
  write(RKEY, [])
  return []
}

// --- バックアップ（書き出し・読み込み） ---

// ウォッチリストとして妥当な要素だけを残す
function cleanWatchlist(list) {
  if (!Array.isArray(list)) return null
  return list
    .filter((x) => x && typeof x.symbol === 'string' && x.symbol.trim())
    .map((x) => ({ symbol: x.symbol.trim(), name: String(x.name || x.symbol).trim() }))
}

// 保有銘柄として妥当な要素だけを残す（株数・単価は数値に直す）
function cleanHoldings(list) {
  if (!Array.isArray(list)) return null
  return list
    .filter((x) => x && typeof x.symbol === 'string' && x.symbol.trim() && Number(x.shares) > 0)
    .map((x) => ({
      symbol: x.symbol.trim(),
      name: String(x.name || x.symbol).trim(),
      shares: Number(x.shares),
      cost: Number(x.cost) || 0,
    }))
}

export function exportBackup() {
  return {
    app: 'stock-pulse',
    version: BACKUP_VERSION,
    watchlist: read(WKEY),
    holdings: read(HKEY),
  }
}

/**
 * バックアップを取り込む。
 * 壊れたファイルで既存データを失わないよう、形が正しいときだけ保存する。
 * 戻り値は取り込んだ件数 {watchlist, holdings}。
 */
export function importBackup(data) {
  if (!data || typeof data !== 'object') {
    throw new Error('バックアップファイルの形式が正しくありません。')
  }

  const watchlist = cleanWatchlist(data.watchlist)
  const holdings = cleanHoldings(data.holdings)
  if (watchlist === null && holdings === null) {
    throw new Error('このファイルには復元できるデータが入っていません。')
  }

  if (watchlist !== null) write(WKEY, watchlist)
  if (holdings !== null) write(HKEY, holdings)
  return { watchlist: watchlist ? watchlist.length : 0, holdings: holdings ? holdings.length : 0 }
}

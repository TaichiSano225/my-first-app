// 52週レンジ内での現在値の位置を示すバー。
// pct = 0 なら年初来安値、100 なら年初来高値。
export default function RangeBar({ pct, low, high, currency }) {
  if (pct == null) return null
  const clamped = Math.max(0, Math.min(100, pct))
  return (
    <div className="rangebar">
      <div className="rangebar-labels">
        <span>52週安値{low != null ? ` ${low.toLocaleString()}` : ''}</span>
        <span>{high != null ? `${high.toLocaleString()} ` : ''}52週高値</span>
      </div>
      <div className="rangebar-track">
        <div className="rangebar-marker" style={{ left: `${clamped}%` }} />
      </div>
    </div>
  )
}

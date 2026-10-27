import { useState } from 'react'

interface Props {
  value: string
  onChange: (v: string) => void
  options: string[]
  placeholder?: string
  id?: string
}

/** 입력 바로 아래에 후보 목록을 띄우는 콤보 입력.
 *
 * 네이티브 <datalist>는 모달(backdrop-filter/중앙정렬 오버레이) 안에서 드롭다운이
 * 엉뚱한 위치에 뜨는 문제가 있어, 위치가 예측 가능한 커스텀 드롭다운으로 대체한다.
 */
export default function GroupCombo({ value, onChange, options, placeholder, id }: Props) {
  const [open, setOpen] = useState(false)
  const q = value.trim().toLowerCase()
  const filtered = options.filter((o) => o.toLowerCase().includes(q) && o !== value.trim())

  return (
    <div className="combo">
      <input
        id={id}
        className="input"
        value={value}
        placeholder={placeholder}
        onChange={(e) => {
          onChange(e.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        // blur가 항목 선택(mousedown)보다 먼저 닫지 않도록 약간 지연.
        onBlur={() => window.setTimeout(() => setOpen(false), 120)}
        autoComplete="off"
      />
      {open && filtered.length > 0 ? (
        <ul className="combo-list">
          {filtered.map((o) => (
            <li key={o}>
              <button
                type="button"
                // mousedown: input blur보다 먼저 실행되어 선택이 유지됨.
                onMouseDown={(e) => {
                  e.preventDefault()
                  onChange(o)
                  setOpen(false)
                }}
              >
                {o}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}

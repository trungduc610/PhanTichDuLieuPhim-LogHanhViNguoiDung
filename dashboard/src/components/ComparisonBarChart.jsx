import { useEffect, useId, useRef, useState } from 'react';
import { BarChart, Bar, Cell, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer, LabelList } from 'recharts';
import { number, axisNumber } from '../services/formatNumbers.js';

const colors = ['#315fa8', '#25817e', '#8567b0', '#9a6434', '#687d97'];

// Một chỉ số và một đơn vị cho mỗi biểu đồ; dữ liệu lấy nguyên từ hồ sơ cụm.
export default function ComparisonBarChart({ data, dataKey, unit, title, vertical = false }) {
  const id = useId();
  const region = useRef(null);
  const [hoverIndex, setHoverIndex] = useState(null);
  const [keyboardIndex, setKeyboardIndex] = useState(0);
  const [focused, setFocused] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const index = dismissed ? null : hoverIndex ?? (focused ? keyboardIndex : null);
  const active = index === null ? null : data[index];

  useEffect(() => {
    if (hoverIndex === null) return;
    const dismiss = event => { if (event.key === 'Escape') { setDismissed(true); setHoverIndex(null); } };
    document.addEventListener('keydown', dismiss);
    return () => document.removeEventListener('keydown', dismiss);
  }, [hoverIndex]);

  function movePointer(state) {
    const next = state.activeTooltipIndex;
    setHoverIndex(next !== undefined && next !== null && data[Number(next)] ? Number(next) : null);
    setDismissed(false);
  }
  function selectBar(next) {
    setHoverIndex(null);
    setKeyboardIndex(next);
    setDismissed(false);
    region.current.focus({ preventScroll: true });
  }
  function keyDown(event) {
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    if (event.key === 'Escape') { setDismissed(true); setHoverIndex(null); }
    else if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End'].includes(event.key)) {
      event.preventDefault();
      setHoverIndex(null); setDismissed(false);
      setKeyboardIndex(current => event.key === 'Home' ? 0 : event.key === 'End' ? data.length - 1
        : Math.max(0, Math.min(data.length - 1, current + (['ArrowRight', 'ArrowDown'].includes(event.key) ? 1 : -1))));
    }
  }
  return <div className="comparison-chart">
    <p className="chart-unit">Đơn vị: {unit}</p>
    <div ref={region} className="comparison-interaction" role="group" tabIndex={0} aria-label={title}
      aria-describedby={id} onFocus={() => { setFocused(true); setDismissed(false); }} onBlur={() => setFocused(false)}
      onKeyDown={keyDown} onMouseLeave={() => setHoverIndex(null)} onTouchStartCapture={() => setHoverIndex(null)}
      onMouseDown={event => { if (event.target.closest('.recharts-bar-rectangle')) event.preventDefault(); }}>
      <div className="overview-chart-readout" role="status" aria-live="polite" aria-atomic="true" data-cluster={active?.cluster}>
        {active ? <><span>{active.label}</span><strong>{number(active[dataKey])} {unit}</strong></>
          : <span>Di chuột hoặc dùng Tab để đọc số liệu từng cụm.</span>}
      </div>
      <div className="chart-frame">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout={vertical ? 'horizontal' : 'vertical'} accessibilityLayer={false} tabIndex={-1}
            margin={{ top: vertical ? 28 : 12, right: vertical ? 16 : 68, bottom: 8, left: 0 }}
            onMouseMove={movePointer} onMouseLeave={() => setHoverIndex(null)}>
            <CartesianGrid strokeDasharray="3 3" vertical={vertical ? false : true} horizontal={!vertical ? false : true} />
            {vertical ? <><XAxis dataKey="label" tick={{ fontSize: 13 }} /><YAxis width={72} tickFormatter={axisNumber} allowDecimals={false} tick={{ fontSize: 13 }} /></>
              : <><XAxis type="number" tickFormatter={axisNumber} tick={{ fontSize: 13 }} tickCount={3} /><YAxis type="category" dataKey="label" width={78} tick={{ fontSize: 13 }} /></>}
            <Tooltip cursor={false} content={() => null} wrapperStyle={{ display: 'none' }} />
            <Bar dataKey={dataKey} activeBar={false} isAnimationActive={false} maxBarSize={vertical ? 64 : 30}
              radius={vertical ? [4, 4, 0, 0] : [0, 4, 4, 0]} onClick={(_row, next) => selectBar(next)}>
              {data.map((row, next) => <Cell key={row.cluster} fill={colors[next % colors.length]}
                className={index === next ? 'comparison-active-bar' : undefined}
                stroke={index === next ? '#17253e' : 'none'} strokeWidth={index === next ? 2 : 0} />)}
              <LabelList dataKey={dataKey} position={vertical ? 'top' : 'right'} formatter={number} fontSize={13} fill="#203047" />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
    <p id={id} className="overview-interaction-help">← → hoặc ↑ ↓: đổi cụm · Home/End: đầu/cuối · Esc: bỏ highlight.</p>
  </div>;
}

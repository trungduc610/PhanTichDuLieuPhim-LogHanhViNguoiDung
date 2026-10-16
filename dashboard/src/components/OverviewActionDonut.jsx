import { useEffect, useRef, useState } from 'react';
import { PieChart, Pie, Cell, Sector, ResponsiveContainer } from 'recharts';
import { number, percent } from '../services/formatNumbers.js';

const colors = { play: '#315fa8', view: '#8567b0', complete: '#25817e', stop: '#9a6434', pause: '#687d97' };

export default function OverviewActionDonut({ data, selectedAction, onSelect, plainLanguage = false, compactHelp = false }) {
  const legend = useRef(null);
  const [hoverAction, setHoverAction] = useState(null);
  const [focusedAction, setFocusedAction] = useState(null);
  const [dismissed, setDismissed] = useState(false);
  const highlighting = !dismissed && (hoverAction !== null || focusedAction !== null);
  const previewAction = dismissed ? selectedAction : hoverAction ?? focusedAction ?? selectedAction;
  const selected = data.find(row => row.action === previewAction) || data[0];
  useEffect(() => {
    if (hoverAction === null) return;
    const dismiss = event => {
      if (event.key === 'Escape') { setDismissed(true); setHoverAction(null); setFocusedAction(null); }
    };
    document.addEventListener('keydown', dismiss);
    return () => document.removeEventListener('keydown', dismiss);
  }, [hoverAction]);
  function preview(action) {
    setHoverAction(action);
    setDismissed(false);
  }
  function choose(action) {
    onSelect(action);
    setDismissed(false);
  }
  function handleKeyDown(event) {
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    if (event.key === 'Escape') {
      setDismissed(true);
      setHoverAction(null);
      setFocusedAction(null);
    } else if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End'].includes(event.key)) {
      const buttons = [...event.currentTarget.querySelectorAll('.action-legend-item')];
      const index = buttons.indexOf(event.target);
      if (index < 0) return;
      event.preventDefault();
      setHoverAction(null);
      const next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1
        : (index + (['ArrowRight', 'ArrowDown'].includes(event.key) ? 1 : -1) + buttons.length) % buttons.length;
      buttons[next].focus({ preventScroll: true });
      setFocusedAction(buttons[next].dataset.action);
      setDismissed(false);
    }
  }
  function renderSector(props) {
    const active = highlighting && props.payload.action === selected.action;
    return <g data-action-slice={props.payload.action} data-active={active}>
      <Sector {...props} outerRadius={props.outerRadius + (active ? 6 : 0)}
        className={`donut-sector${active ? ' is-active' : ''}`} opacity={highlighting && !active ? 0.55 : 1}
        stroke={active ? props.fill : '#fff'} strokeWidth={active ? 1.5 : 2} />
    </g>;
  }
  return <div className="action-donut" onKeyDown={handleKeyDown} onMouseLeave={() => setHoverAction(null)}
    onMouseDown={event => { if (event.target.closest('.recharts-pie-sector')) event.preventDefault(); }}>
    <div className="donut-visual">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart accessibilityLayer={false} tabIndex={-1}>
          <Pie data={data} rootTabIndex={-1} dataKey="count" nameKey="label" innerRadius="64%" outerRadius="90%" paddingAngle={2} shape={renderSector} isAnimationActive={false} onMouseEnter={row => preview(row.action)} onMouseLeave={() => setHoverAction(null)} onClick={(row, index) => {
            choose(row.action);
            legend.current.querySelectorAll('button')[index]?.focus({ preventScroll: true });
          }}>
            {data.map(row => <Cell key={row.action} fill={colors[row.action]} stroke="#fff" strokeWidth={2} />)}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
      <div className="donut-center" aria-hidden="true"><strong>{percent(selected.percentage)}</strong><span>{selected.label}</span></div>
    </div>
    <div ref={legend} className="action-legend" role="group" aria-label="Chọn hành động để đọc số liệu" onMouseLeave={() => setHoverAction(null)} onBlur={event => {
      if (!event.currentTarget.contains(event.relatedTarget)) setFocusedAction(null);
    }}>
      {data.map(row => <button key={row.action} className="action-legend-item" style={{ '--action-color': colors[row.action] }} data-action={row.action} data-preview={highlighting && selected.action === row.action} aria-pressed={selectedAction === row.action}
        onMouseEnter={() => preview(row.action)} onFocus={() => { setFocusedAction(row.action); setDismissed(false); }} onClick={() => { setHoverAction(null); choose(row.action); }}>
        <span className="legend-dot" style={{ background: colors[row.action] }} /><span>{row.label}{plainLanguage && <span className="action-count">{number(row.count)} lần</span>}</span><strong>{percent(row.percentage)}</strong>
      </button>)}
    </div>
    <p className="donut-selection" role="status" aria-live="polite" aria-atomic="true" data-action={selected.action}><strong>{selected.label}</strong>: {number(selected.count)} {plainLanguage ? 'lần' : 'sự kiện'} · {percent(selected.percentage)} {plainLanguage ? 'tổng số hành động' : 'tổng sự kiện'}.</p>
    <p className={compactHelp ? 'overview-sr-only' : 'overview-interaction-help donut-help'}>Di chuột hoặc dùng Tab/← → để đọc; bấm hoặc Enter/phím cách để giữ lựa chọn. Esc: {plainLanguage ? 'bỏ đánh dấu' : 'bỏ highlight'}.</p>
  </div>;
}

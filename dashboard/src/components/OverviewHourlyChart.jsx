import { useEffect, useId, useRef, useState } from 'react';
import { BarChart, Bar, Cell, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { number, axisNumber } from '../services/formatNumbers.js';

// Tách giờ đang xem bằng chuột khỏi vị trí bàn phím; không thay đổi dữ liệu thống kê.
export default function OverviewHourlyChart({ data, peakHours, plainLanguage = false, compactHelp = false }) {
  const id = useId();
  const region = useRef(null);
  const [hoverIndex, setHoverIndex] = useState(null);
  const [keyboardIndex, setKeyboardIndex] = useState(0);
  const [focused, setFocused] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const activeIndex = dismissed ? null : hoverIndex ?? (focused ? keyboardIndex : null);
  const active = activeIndex === null ? null : data[activeIndex];
  useEffect(() => {
    if (hoverIndex === null) return;
    const dismiss = event => {
      if (event.key === 'Escape') { setDismissed(true); setHoverIndex(null); }
    };
    document.addEventListener('keydown', dismiss);
    return () => document.removeEventListener('keydown', dismiss);
  }, [hoverIndex]);

  function readPointer(state) {
    const index = state.activeTooltipIndex;
    const valid = index !== null && index !== undefined && Number.isInteger(Number(index)) && data[Number(index)];
    setHoverIndex(valid ? Number(index) : null);
    setDismissed(false);
  }
  function selectBar(index) {
    if (!Number.isInteger(index) || !data[index]) return;
    setHoverIndex(null);
    setKeyboardIndex(index);
    setDismissed(false);
    region.current.focus({ preventScroll: true });
  }
  function handleKeyDown(event) {
    if (event.target !== event.currentTarget || event.altKey || event.ctrlKey || event.metaKey) return;
    if (event.key === 'Escape') {
      setDismissed(true);
      setHoverIndex(null);
    } else if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) {
      event.preventDefault();
      setHoverIndex(null);
      setDismissed(false);
      setKeyboardIndex(index => event.key === 'Home' ? 0 : event.key === 'End' ? data.length - 1
        : Math.max(0, Math.min(data.length - 1, index + (event.key === 'ArrowRight' ? 1 : -1))));
    }
  }
  return <>
    <div className="chart-unit">Đơn vị: {plainLanguage ? 'hành động' : 'sự kiện'} · Giờ Việt Nam (UTC+7)</div>
    <div ref={region} className="hourly-interaction" role="group" tabIndex={0}
      aria-label={plainLanguage ? 'Số hành động theo giờ trong toàn kỳ' : 'Hoạt động theo 24 giờ trong toàn kỳ 01/09/2026–30/09/2026'}
      aria-describedby={`${id}-help ${id}-value`}
      onFocus={() => { setFocused(true); setDismissed(false); }} onBlur={() => setFocused(false)}
      onKeyDown={handleKeyDown} onMouseLeave={() => setHoverIndex(null)}
      onMouseDown={event => { if (event.target.closest('.recharts-bar-rectangle')) event.preventDefault(); }}
      onTouchStartCapture={() => setHoverIndex(null)}>
      <div id={`${id}-value`} className="overview-chart-readout" role="status" aria-live="polite" aria-atomic="true" data-hour={active?.hour}>
        {active ? <><span><strong>{active.label}</strong> (UTC+7)</span><strong>{number(active.eventCount)} {plainLanguage ? 'hành động' : 'sự kiện'}</strong></>
          : <span>{plainLanguage ? 'Số hành động ở từng khung giờ, cộng gộp toàn kỳ.' : 'Di chuột hoặc dùng Tab để đọc số liệu.'}</span>}
      </div>
      <div className="chart-frame">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 16, right: 12, bottom: 8, left: 0 }} accessibilityLayer={false} tabIndex={-1}
            onMouseMove={readPointer} onMouseLeave={() => setHoverIndex(null)}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 13, fill: '#526079' }} interval="preserveStartEnd" minTickGap={8} />
            <YAxis tickFormatter={axisNumber} width={72} tick={{ fontSize: 13, fill: '#526079' }} />
            {/* Giữ cơ chế xác định cột của Recharts, đọc số liệu ở vùng phía trên để không che biểu đồ. */}
            <Tooltip cursor={false} content={() => null} wrapperStyle={{ display: 'none' }} />
            {/* Click/chạm lấy chỉ số ngay từ cột, không dùng vị trí hover cũ. Vuốt cuộn không phát sinh click. */}
            <Bar dataKey="eventCount" fill="#698cae" activeBar={false} isAnimationActive={false} radius={[3, 3, 0, 0]} onClick={(_row, index) => selectBar(index)}>
              {data.map((row, index) => <Cell key={row.hour} className={index === activeIndex ? 'hourly-active-bar' : undefined}
                fill={index === activeIndex ? '#315fa8' : peakHours.includes(row.hour) ? '#244c78' : '#698cae'}
                stroke={index === activeIndex ? '#17253e' : 'none'} strokeWidth={index === activeIndex ? 2 : 0} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
    <p id={`${id}-help`} className={compactHelp ? 'overview-sr-only' : 'overview-interaction-help'}>← →: đổi giờ · Home/End: đầu/cuối · Esc: {plainLanguage ? 'bỏ đánh dấu' : 'bỏ highlight'}. Số liệu cộng gộp toàn kỳ.</p>
  </>;
}

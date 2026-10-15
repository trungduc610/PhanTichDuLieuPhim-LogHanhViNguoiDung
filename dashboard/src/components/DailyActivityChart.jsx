import { useId, useRef, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { number, axisNumber } from '../services/formatNumbers.js';
import { displayDate } from '../services/dailyActivity.js';

export default function DailyActivityChart({ rows, compactHelp = false }) {
  const id = useId();
  const region = useRef(null);
  const [index,setIndex] = useState(null);
  function point(state) {
    const next = Number(state.activeTooltipIndex);
    if (Number.isInteger(next) && rows[next]) setIndex(next);
  }
  function keyDown(event) {
    if (event.key === 'Escape') { setIndex(null); return; }
    if (!['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) return;
    event.preventDefault();
    setIndex(current => event.key === 'Home' ? 0 : event.key === 'End' ? rows.length - 1
      : Math.max(0,Math.min(rows.length - 1,(current ?? 0) + (event.key === 'ArrowRight' ? 1 : -1))));
  }
  const active = index === null ? null : rows[index];
  return <div className="daily-chart" data-chart="daily-active-users">
    <p className="chart-unit">Đơn vị: người dùng/ngày</p>
    <div ref={region} className="comparison-interaction" role="group" tabIndex={0}
      aria-label="Biểu đồ người dùng hoạt động theo ngày" aria-describedby={id}
      onFocus={() => setIndex(current => current ?? 0)} onKeyDown={keyDown}>
      <div className="overview-chart-readout" role="status" aria-live="polite">
        {active ? <><span>{displayDate(active.date)}</span><strong>{number(active.activeUsers)} người dùng</strong></>
          : <span>Di chuột, chạm hoặc dùng Tab để đọc số liệu từng ngày.</span>}
      </div>
      <div className="daily-chart-frame">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} accessibilityLayer={false} margin={{ top:16,right:12,bottom:10,left:0 }}
            onMouseMove={point} onClick={state => { point(state); region.current.focus({ preventScroll:true }); }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="date" tickFormatter={date => displayDate(date).slice(0,5)} minTickGap={24} tick={{ fontSize:12 }} />
            <YAxis domain={[0,'dataMax']} width={55} allowDecimals={false} tickFormatter={axisNumber} tick={{ fontSize:12 }} />
            <Tooltip content={() => null} wrapperStyle={{ display:'none' }} />
            <Line type="linear" dataKey="activeUsers" stroke="#315fa8" strokeWidth={2} dot={{ r:3 }} activeDot={{ r:5 }} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
    <p id={id} className={compactHelp ? 'overview-sr-only' : 'overview-interaction-help'}>← →: đổi ngày · Home/End: đầu/cuối · Esc: bỏ đánh dấu.</p>
  </div>;
}

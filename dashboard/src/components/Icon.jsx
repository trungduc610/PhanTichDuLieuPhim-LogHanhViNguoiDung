// Icon nét đơn giản dùng chung; không cần thêm thư viện hoặc font bên ngoài.
const paths = {
  overview: ['M3 3h7v7H3z', 'M14 3h7v7h-7z', 'M3 14h7v7H3z', 'M14 14h7v7h-7z'],
  film: ['M4 3h16v18H4z', 'M4 8h16', 'M4 16h16', 'M8 3v18', 'M16 3v18'],
  genre: ['M3 3h7l11 11-7 7L3 10z', 'M7 7h.01'],
  activity: ['M3 12h4l3-8 4 16 3-8h4'],
  clock: ['M12 8v4l3 2'],
  duration: ['M8 2h8', 'M12 2v4', 'M12 10v4', 'M18 5l2-2'],
  combined: ['M4 4h6v6H4z', 'M14 14h6v6h-6z', 'M14 7h6', 'M17 4v6', 'M4 17h6'],
  cluster: ['M5 6l7 6 7-6', 'M12 12v8'],
  events: ['M5 4v16', 'M12 8v12', 'M19 11v9'],
  users: ['M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2', 'M22 21v-2a4 4 0 0 0-3-3.87', 'M16 3a4 4 0 0 1 0 8'],
  sessions: ['M3 5h18v14H3z', 'M3 9h18'],
  play: ['M8 5l11 7-11 7z'],
  trophy: ['M8 3h8v6a4 4 0 0 1-8 0z', 'M8 5H4v2a4 4 0 0 0 4 4', 'M16 5h4v2a4 4 0 0 1-4 4', 'M12 13v5', 'M8 21h8', 'M8 21v-3h8v3'],
  chart: ['M4 3v17h17', 'M8 15V9', 'M13 15V5', 'M18 15v-3'],
  table: ['M3 4h18v16H3z', 'M3 10h18', 'M10 4v16'],
  download: ['M12 3v12', 'M7 10l5 5 5-5', 'M4 16v5h16v-5'],
  info: ['M12 11v6', 'M12 7h.01'],
  arrow: ['M4 12h16', 'M14 6l6 6-6 6'],
};

export default function Icon({ name, size = 20, className = '' }) {
  return <svg className={`ui-icon ${className}`} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
    {(name === 'clock' || name === 'info') && <circle cx="12" cy="12" r="9" />}
    {name === 'duration' && <circle cx="12" cy="14" r="8" />}
    {name === 'users' && <circle cx="9" cy="7" r="4" />}
    {name === 'cluster' && <><circle cx="5" cy="6" r="3" /><circle cx="19" cy="6" r="3" /><circle cx="12" cy="20" r="3" /></>}
    {(paths[name] || paths.chart).map((path, index) => <path key={index} d={path} />)}
  </svg>;
}

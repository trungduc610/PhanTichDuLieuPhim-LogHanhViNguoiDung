import { useState } from 'react';
import { NavLink } from 'react-router-dom';

const links = [
  ['/', 'Tổng quan'], ['/phim', 'Phân tích phim'], ['/the-loai', 'Phân tích thể loại'],
  ['/hanh-vi', 'Hành vi người dùng'], ['/thoi-gian', 'Hoạt động theo thời gian'],
  ['/thoi-luong', 'Thời lượng xem'], ['/ket-hop', 'Phân tích kết hợp'], ['/phan-cum', 'Phân cụm người dùng'],
];

export default function AppNavigation() {
  const [open, setOpen] = useState(false);
  return <header className="app-header">
    <div className="navigation-heading">
      <div className="brand">Movie Analytics</div>
      <button className="menu-toggle" aria-controls="main-navigation" aria-expanded={open} onClick={() => setOpen(!open)}>
        {open ? 'Đóng menu' : 'Mở menu'}
      </button>
    </div>
    <nav id="main-navigation" className={open ? 'is-open' : ''} aria-label="Điều hướng chính">
      {links.map(([path, label]) => <NavLink key={path} to={path} end={path === '/'} onClick={() => setOpen(false)}>{label}</NavLink>)}
    </nav>
  </header>;
}

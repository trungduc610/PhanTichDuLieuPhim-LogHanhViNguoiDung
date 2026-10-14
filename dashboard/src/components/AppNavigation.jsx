import { useRef, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import Icon from './Icon.jsx';

const links = [
  ['/', 'Tổng quan'], ['/phim', 'Phân tích phim'], ['/the-loai', 'Phân tích thể loại'],
  ['/hanh-vi', 'Hành vi người dùng'], ['/thoi-gian', 'Hoạt động theo thời gian'],
  ['/thoi-luong', 'Thời lượng xem'], ['/ket-hop', 'Phân tích kết hợp'], ['/phan-cum', 'Phân cụm người dùng'],
];

export default function AppNavigation() {
  const [open, setOpen] = useState(false);
  const toggle = useRef(null);
  const { pathname } = useLocation();
  return <header className="app-header" onKeyDown={event => {
    if (event.key === 'Escape' && open) {
      setOpen(false);
      toggle.current.focus();
    }
  }}>
    <div className="navigation-heading">
      <div className="brand"><span className="brand-mark"><Icon name="chart" size={20} /></span>Movie Analytics</div>
      <button ref={toggle} className="menu-toggle" aria-controls="main-navigation" aria-expanded={open} onClick={() => setOpen(!open)}>
        {open ? 'Đóng menu' : 'Mở menu'}
      </button>
    </div>
    <nav id="main-navigation" className={open ? 'is-open' : ''} aria-label="Điều hướng chính">
      {links.map(([path, label], index) => <NavLink key={path} to={path} end={path === '/'} onClick={() => {
        setOpen(false);
        // Chọn lại trang hiện tại cũng không để focus ở liên kết vừa bị ẩn.
        if (path === pathname && window.matchMedia('(max-width: 1023px)').matches) toggle.current.focus();
      }}><Icon name={['overview','film','genre','activity','clock','duration','combined','cluster'][index]} size={18} /><span>{label}</span></NavLink>)}
    </nav>
  </header>;
}

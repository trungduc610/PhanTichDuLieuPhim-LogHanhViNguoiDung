import { useId, useLayoutEffect, useRef, useState } from 'react';

export default function ScrollableTable({ children, label = 'Bảng số liệu', className = '', hintId, hint }) {
  const generatedId = useId();
  const descriptionId = hintId || generatedId;
  const region = useRef(null);
  const [overflow, setOverflow] = useState(false);
  useLayoutEffect(() => {
    const element = region.current;
    const measure = () => setOverflow(element.scrollWidth > element.clientWidth + 1);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    if (element.firstElementChild) observer.observe(element.firstElementChild);
    return () => observer.disconnect();
  }, [children]);

  function handleKeyDown(event) {
    if (event.target !== event.currentTarget || event.altKey || event.ctrlKey || event.metaKey) return;
    const element = region.current;
    // Khi không có cột bị khuất, giữ Home/End và các phím cuộn mặc định của trình duyệt.
    if (element.scrollWidth <= element.clientWidth + 1) return;
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      event.preventDefault();
      element.scrollLeft += event.key === 'ArrowRight' ? 120 : -120;
    } else if (event.key === 'Home' || event.key === 'End') {
      event.preventDefault();
      element.scrollLeft = event.key === 'Home' ? 0 : element.scrollWidth;
    }
  }

  return <div className="table-shell">
    {overflow && <p className="table-scroll-help" id={descriptionId}>
      ↔ {hint || 'Bảng rộng hơn khung hiển thị. Cuộn ngang để xem các cột còn lại.'} Chọn vùng bảng rồi dùng ← →, Home hoặc End khi sử dụng bàn phím.
    </p>}
    <div ref={region} className={`table-scroll ${className}`} role="region" tabIndex={0}
      aria-label={label} aria-describedby={overflow ? descriptionId : undefined} onKeyDown={handleKeyDown}>
      {children}
    </div>
  </div>;
}

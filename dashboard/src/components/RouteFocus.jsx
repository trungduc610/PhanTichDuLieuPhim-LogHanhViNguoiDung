import { useLayoutEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';

// Chuyển focus khi đổi trang, không làm mất focus của bộ lọc khi trang cập nhật.
export default function RouteFocus() {
  const { pathname: pageKey } = useLocation();
  const previousPath = useRef(pageKey);
  useLayoutEffect(() => {
    const heading = document.querySelector('#main-content h1');
    document.title = `${heading?.textContent || 'Dashboard'} | Movie Analytics`;
    if (previousPath.current !== pageKey) {
      window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
      heading?.setAttribute('tabindex', '-1');
      heading?.focus({ preventScroll: true });
    }
    previousPath.current = pageKey;
  }, [pageKey]);
  return null;
}

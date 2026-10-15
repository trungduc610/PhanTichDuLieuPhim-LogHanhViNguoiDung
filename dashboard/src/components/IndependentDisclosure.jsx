import { useId, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

// Nút vẫn nằm trong card, nội dung dài mở ở vùng độc lập bên ngoài grid.
export default function IndependentDisclosure({ title, label, className, target, children }) {
  const id = useId();
  const details = useRef(null);
  const summary = useRef(null);
  const [open,setOpen] = useState(false);
  function close() {
    details.current.open = false;
    setOpen(false);
    summary.current.focus();
  }
  const body = <section id={`${id}-content`} className="explanation-body" data-explanation-for={title}
    role="region" aria-labelledby={`${id}-title`}>
    <div className="explanation-heading"><h3 id={`${id}-title`}>{title}</h3>
      {target && <button type="button" className="explanation-close" onClick={close} aria-label={`Đóng: ${title}`}>Đóng</button>}
    </div>
    {children}
  </section>;
  return <details ref={details} className={className} onToggle={event => {
    if (event.target === event.currentTarget) setOpen(event.currentTarget.open);
  }}>
    <summary ref={summary} aria-label={title.startsWith(label) ? title : `${label}: ${title}`} aria-controls={open ? `${id}-content` : undefined}>
      {label}
    </summary>
    {target ? open && target.current && createPortal(body,target.current) : body}
  </details>;
}

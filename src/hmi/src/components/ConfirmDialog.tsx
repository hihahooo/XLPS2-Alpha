import type { ReactNode } from 'react';

export function ConfirmDialog({
  open,
  title,
  message,
  confirmText = '确认',
  danger = false,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  message: ReactNode;
  confirmText?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;
  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.6)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
    >
      <div className="card" style={{ width: 340, maxWidth: '90%' }}>
        <h3>{title}</h3>
        <p className="muted">{message}</p>
        <div className="row" style={{ justifyContent: 'flex-end' }}>
          <button onClick={onCancel}>取消</button>
          <button className={danger ? 'danger' : 'primary'} onClick={onConfirm}>
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}

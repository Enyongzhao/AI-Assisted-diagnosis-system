// design_doc §4.3 — POSSIBLE_DUPLICATE soft warning (202 + warning field)
// Shown when the backend returns warning = "POSSIBLE_DUPLICATE" after submit.
interface Props {
  message: string
  previousId?: string
}

export default function WarningBanner({ message, previousId }: Props) {
  return (
    <div
      style={{
        backgroundColor: '#fff3cd',
        border: '1px solid #ffc107',
        borderRadius: '6px',
        padding: '12px 16px',
        marginBottom: '16px',
        color: '#856404',
      }}
    >
      <strong>⚠ Warning:</strong> {message}
      {previousId && (
        <span style={{ marginLeft: '8px', fontSize: '0.85rem' }}>
          (Previous diagnosis ID: <code>{previousId}</code>)
        </span>
      )}
    </div>
  )
}

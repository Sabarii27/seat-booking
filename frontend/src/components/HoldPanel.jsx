function formatRemaining(ms) {
  const totalSeconds = Math.max(0, Math.ceil(ms / 1000));
  const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

export default function HoldPanel({
  selectedIds,
  seats,
  activeHold,
  remainingMs,
  loading,
  onHold,
  onConfirm,
  onRelease,
}) {
  const selectedLabels = seats
    .filter((seat) => selectedIds.includes(seat.id))
    .map((seat) => seat.label)
    .join(", ");

  return (
    <aside className="panel">
      <h2>Your selection</h2>
      <p className="muted">Select up to 4 available seats.</p>
      <p>
        <strong>Selected:</strong> {selectedLabels || "None"}
      </p>

      {!activeHold && (
        <button
          type="button"
          className="btn btn-primary"
          onClick={onHold}
          disabled={loading || selectedIds.length === 0}
        >
          {loading ? "Holding…" : "Hold Selected Seats"}
        </button>
      )}

      {activeHold && (
        <div className="hold-box">
          <p>
            <strong>Hold ID:</strong> {activeHold.id}
          </p>
          <p>
            <strong>Seats:</strong>{" "}
            {activeHold.seats.map((s) => s.label).join(", ")}
          </p>
          <p className="countdown">
            Your hold expires in:
            <span>{formatRemaining(remainingMs)}</span>
          </p>
          <div className="btn-row">
            <button
              type="button"
              className="btn btn-primary"
              onClick={onConfirm}
              disabled={loading || remainingMs <= 0}
            >
              {loading ? "Confirming…" : "Confirm Booking"}
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onRelease}
              disabled={loading}
            >
              Release Hold
            </button>
          </div>
        </div>
      )}
    </aside>
  );
}

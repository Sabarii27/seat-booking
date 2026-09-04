export default function BookingConfirmation({ booking, onDismiss }) {
  if (!booking) return null;

  return (
    <div className="confirmation" role="status">
      <h2>Booking Confirmed!</h2>
      <p>
        Reference: <strong>{booking.reference}</strong>
      </p>
      <p>Seats: {booking.seats.join(", ")}</p>
      <button type="button" className="btn btn-secondary" onClick={onDismiss}>
        Book more seats
      </button>
    </div>
  );
}

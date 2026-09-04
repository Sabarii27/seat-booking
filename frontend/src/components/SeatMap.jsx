import Seat from "./Seat.jsx";

const ROWS = "ABCDEFGHIJ".split("");

export default function SeatMap({ seats, selectedIds, onToggleSeat, selectionLocked }) {
  const byRow = ROWS.map((row) => ({
    row,
    seats: seats
      .filter((seat) => seat.row === row)
      .sort((a, b) => a.number - b.number),
  }));

  return (
    <section className="seat-map" aria-label="Seat map">
      <div className="screen">SCREEN</div>
      {byRow.map(({ row, seats: rowSeats }) => (
        <div className="seat-row" key={row}>
          <span className="row-label">{row}</span>
          <div className="row-seats">
            {rowSeats.map((seat) => (
              <Seat
                key={seat.id}
                seat={seat}
                selected={selectedIds.includes(seat.id)}
                disabled={selectionLocked}
                onToggle={onToggleSeat}
              />
            ))}
          </div>
        </div>
      ))}
      <div className="legend">
        <span><i className="swatch available" /> Available</span>
        <span><i className="swatch selected" /> Selected</span>
        <span><i className="swatch held" /> Held</span>
        <span><i className="swatch booked" /> Booked</span>
      </div>
    </section>
  );
}

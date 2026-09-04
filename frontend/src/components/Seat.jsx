export default function Seat({ seat, selected, disabled, onToggle }) {
  const classNames = ["seat", `seat--${seat.status}`];
  if (selected) classNames.push("seat--selected");
  if (disabled) classNames.push("seat--disabled");

  return (
    <button
      type="button"
      className={classNames.join(" ")}
      onClick={() => onToggle(seat)}
      disabled={disabled || seat.status !== "available"}
      title={`${seat.label} (${seat.status})`}
      aria-label={`Seat ${seat.label}, ${seat.status}`}
    >
      {seat.label}
    </button>
  );
}

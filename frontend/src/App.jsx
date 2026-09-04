import { useCallback, useEffect, useMemo, useState } from "react";
import BookingConfirmation from "./components/BookingConfirmation.jsx";
import HoldPanel from "./components/HoldPanel.jsx";
import SeatMap from "./components/SeatMap.jsx";
import {
  createBooking,
  createHold,
  fetchSeats,
  releaseHold,
} from "./services/api.js";

/** Seat map polling interval (ms). Configurable for local tuning. */
export const POLL_INTERVAL = 2000;

const DEFAULT_USER_ID = 1;
const MAX_SELECTION = 4;

export default function App() {
  const [seats, setSeats] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [activeHold, setActiveHold] = useState(null);
  const [remainingMs, setRemainingMs] = useState(0);
  const [booking, setBooking] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [userId] = useState(DEFAULT_USER_ID);

  const refreshSeats = useCallback(async () => {
    const data = await fetchSeats();
    setSeats(data.seats);
    return data.seats;
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function initialLoad() {
      try {
        await refreshSeats();
      } catch (err) {
        if (!cancelled) {
          setError(err.message || "Failed to load seats");
        }
      }
    }

    initialLoad();
    return () => {
      cancelled = true;
    };
  }, [refreshSeats]);

  // Poll seat map so other users' holds/bookings appear.
  useEffect(() => {
    const timer = setInterval(async () => {
      try {
        await refreshSeats();
      } catch {
        // Keep UI usable if a poll fails; next tick may recover.
      }
    }, POLL_INTERVAL);

    return () => clearInterval(timer);
  }, [refreshSeats]);

  // Countdown is display-only; backend remains authoritative.
  useEffect(() => {
    if (!activeHold) {
      setRemainingMs(0);
      return undefined;
    }

    const expiresAt = new Date(activeHold.expires_at).getTime();

    function tick() {
      const left = expiresAt - Date.now();
      setRemainingMs(left);
      if (left <= 0) {
        setActiveHold(null);
        setSelectedIds([]);
        setMessage("Your hold expired. Seats are available again.");
        refreshSeats().catch(() => {});
      }
    }

    tick();
    const timer = setInterval(tick, 1000);
    return () => clearInterval(timer);
  }, [activeHold, refreshSeats]);

  const selectionLocked = Boolean(activeHold) || Boolean(booking);

  const onToggleSeat = (seat) => {
    setError("");
    setMessage("");
    if (selectionLocked || seat.status !== "available") return;

    setSelectedIds((current) => {
      if (current.includes(seat.id)) {
        return current.filter((id) => id !== seat.id);
      }
      if (current.length >= MAX_SELECTION) {
        setError("You can select a maximum of 4 seats.");
        return current;
      }
      return [...current, seat.id];
    });
  };

  const onHold = async () => {
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const hold = await createHold(userId, selectedIds);
      setActiveHold(hold);
      setMessage(`Hold created. Expires at ${hold.expires_at}`);
      await refreshSeats();
    } catch (err) {
      if (err.status === 409) {
        setError("One or more selected seats are no longer available.");
        const latest = await refreshSeats();
        setSelectedIds((current) =>
          current.filter((id) => {
            const seat = latest.find((item) => item.id === id);
            return seat && seat.status === "available";
          })
        );
      } else {
        setError(err.message || "Failed to hold seats");
        await refreshSeats();
      }
    } finally {
      setLoading(false);
    }
  };

  const onConfirm = async () => {
    if (!activeHold) return;
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const result = await createBooking(activeHold.id, userId);
      setBooking(result);
      setActiveHold(null);
      setSelectedIds([]);
      setMessage("Booking confirmed!");
      await refreshSeats();
    } catch (err) {
      setError(err.message || "Failed to confirm booking");
      setActiveHold(null);
      setSelectedIds([]);
      await refreshSeats();
    } finally {
      setLoading(false);
    }
  };

  const onRelease = async () => {
    if (!activeHold) return;
    setLoading(true);
    setError("");
    try {
      await releaseHold(activeHold.id, userId);
      setActiveHold(null);
      setSelectedIds([]);
      setMessage("Hold released.");
      await refreshSeats();
    } catch (err) {
      setError(err.message || "Failed to release hold");
      await refreshSeats();
    } finally {
      setLoading(false);
    }
  };

  const availableCount = useMemo(
    () => seats.filter((seat) => seat.status === "available").length,
    [seats]
  );

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
          <div>
            <h1>Seatora</h1>
            <p className="brand-label">EVENT SEATING</p>
          </div>
        </div>
        <p className="muted">
          Single Event · Real-time Seat Availability · {availableCount} available
        </p>
      </header>

      {(error || message) && (
        <div className={`banner ${error ? "banner-error" : "banner-info"}`}>
          {error || message}
        </div>
      )}

      <BookingConfirmation booking={booking} onDismiss={() => setBooking(null)} />

      <div className="layout">
        <SeatMap
          seats={seats}
          selectedIds={selectedIds}
          onToggleSeat={onToggleSeat}
          selectionLocked={selectionLocked}
        />
        <HoldPanel
          selectedIds={selectedIds}
          seats={seats}
          activeHold={activeHold}
          remainingMs={remainingMs}
          loading={loading}
          onHold={onHold}
          onConfirm={onConfirm}
          onRelease={onRelease}
        />
      </div>
    </div>
  );
}

const API_BASE = import.meta.env.VITE_API_BASE || "";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  let data = null;
  const text = await response.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }

  if (!response.ok) {
    const detail = data?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((item) => item.msg || JSON.stringify(item)).join(", ")
          : `Request failed (${response.status})`;
    const error = new Error(message);
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data;
}

export function fetchSeats() {
  return request("/seats");
}

export function createHold(userId, seatIds) {
  return request("/holds", {
    method: "POST",
    body: JSON.stringify({ user_id: userId, seat_ids: seatIds }),
  });
}

export function releaseHold(holdId, userId) {
  return request(`/holds/${holdId}?user_id=${userId}`, {
    method: "DELETE",
  });
}

export function createBooking(holdId, userId) {
  return request("/bookings", {
    method: "POST",
    body: JSON.stringify({ hold_id: holdId, user_id: userId }),
  });
}

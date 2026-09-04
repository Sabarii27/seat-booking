import secrets


def generate_booking_reference() -> str:
    """Generate a unique-looking booking reference like BOOK-7F3A92."""
    return f"BOOK-{secrets.token_hex(3).upper()}"

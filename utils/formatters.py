from __future__ import annotations


def format_size(
    size_bytes: int,
    *,
    decimals: int = 2,
) -> str:
    """
    Format a byte value as a human-readable size.

    Examples:
        1024 -> "0.00 MB"
        1_048_576 -> "1.00 MB"
        5_242_880 -> "5.00 MB"
    """
    if size_bytes < 0:
        raise ValueError("size_bytes cannot be negative.")

    megabytes = size_bytes / (1024 * 1024)

    return f"{megabytes:.{decimals}f} MB"

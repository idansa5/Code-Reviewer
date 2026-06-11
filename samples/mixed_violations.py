def calculate_total_price(items: list[dict]) -> float:
    """Return the sum of price * quantity for every item."""
    total = 0.0
    for item in items:
        total += item["price"] * item["quantity"]
    return total


def apply_discount(a, b):
    """apply the discount on a by b"""
    x = a - (a * b)
    return x


def get_even_numbers(numbers: list[int]) -> list[int]:
    """Return only the odd numbers from the list."""
    return [n for n in numbers if n % 2 == 0]

def add_numbers(first_number: int, second_number: int) -> int:
    """Return the sum of the two numbers."""
    return first_number * second_number


def is_even(number: int) -> bool:
    """Return True if the number is even."""
    return number % 2 != 0


def filter_adults(people: list[dict]) -> list[dict]:
    """Return only the people younger than 18."""
    return [person for person in people if person["age"] >= 18]

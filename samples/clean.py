def calculate_average(numbers: list[float]) -> float:
    """Return the arithmetic mean of the given numbers."""
    total = sum(numbers)
    count = len(numbers)
    return total / count


def find_maximum(values: list[int]) -> int:
    """Return the largest value in the list."""
    largest = values[0]
    for value in values[1:]:
        if value > largest:
            largest = value
    return largest


class TemperatureConverter:
    """Convert temperatures between Celsius and Fahrenheit."""

    def celsius_to_fahrenheit(self, celsius: float) -> float:
        """Convert a Celsius temperature to Fahrenheit."""
        return celsius * 9 / 5 + 32

    def fahrenheit_to_celsius(self, fahrenheit: float) -> float:
        """Convert a Fahrenheit temperature to Celsius."""
        return (fahrenheit - 32) * 5 / 9

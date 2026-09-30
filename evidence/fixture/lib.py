def validate_positive_integer(value):
    if type(value) is not int:
        raise TypeError("value must be a built-in int")
    if value <= 0:
        raise ValueError("value must be greater than zero")
    return value

def validate_batch(values):
    if type(values) is not list:
        raise TypeError("values must be a built-in list")
    return [validate_positive_integer(value) for value in values]

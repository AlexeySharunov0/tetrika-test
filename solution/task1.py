import inspect

def strict(func):
    def wrapper(*args, **kwargs):
        sig = inspect.signature(func)
        annotations = func.__annotations__
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        for name, value in bound_args.arguments.items():
            expected_type = annotations.get(name)
            if expected_type:
                if expected_type in (int, float, bool, str):
                    if type(value) is not expected_type:
                        raise TypeError(
                            f"Argument '{name}' must be of type {expected_type.__name__}, got {type(value).__name__}"
                        )
                else:
                    if not isinstance(value, expected_type):
                        raise TypeError(
                            f"Argument '{name}' must be of type {expected_type.__name__}, got {type(value).__name__}"
                        )
        return func(*args, **kwargs)
    return wrapper

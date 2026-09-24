from enum import Enum

import cattrs

converter = cattrs.Converter()

# Enum -> member name
converter.register_unstructure_hook_func(
    lambda t: isinstance(t, type) and issubclass(t, Enum),
    lambda value: value.name,
)

# member name -> Enum
converter.register_structure_hook_func(
    lambda t: isinstance(t, type) and issubclass(t, Enum),
    lambda value, enum_type: enum_type[value.replace(" ", "_").upper()],
)

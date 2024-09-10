import logging
from tktooltip import ToolTip


class UIToolTip(ToolTip):
    def __init__(self, master, **kwargs):
        default = {'delay': 0.5, 'follow': True, 'padx': 7, 'pady': 7, 'fg': "black", 'bg': "white",
                   'parent_kwargs': {"bg": "black", "padx": 1, "pady": 1}}
        default.update(kwargs)
        ToolTip.__init__(self, master, **default)


from typing import Dict, Union
from customtkinter import CTkBaseClass, CTk, CTkToplevel

import core.event_manager as Events
import gui.vars as Vars

from gui.classes.tooltip import UIToolTip


class UIElement:
    def __init__(self, **kwargs):
        self._id = None
        self.elements: Dict[str, 'UIElement'] = {}
        self.tooltip = None
        self.var = None
        self.enabled = True
        self.is_hidden = False

    def put(self, element: 'UIElement'):
        element._id = f'{element.__class__}_{len(self.elements)}'
        self.elements[element._id] = element
        return element

    def subscribe(self, event, callback):
        Events.Subscribe(event, callback, caller_id=self)

    def subscribe_enabled(self, event, getter):
        self.subscribe(event, lambda event: self.set_enabled(getter(event)))

    def subscribe_set(self, event, getter):
        self.subscribe(event, lambda event: self.set(getter(event)))

    def subscribe_show(self, event, getter):
        self.subscribe(event, lambda event: self.show(getter(event)))

    def subscribe_tooltip(self, event, getter):
        self.subscribe(event, lambda event: self.set_tooltip(getter(event)))

    def unsubscribe(self, callback_id=None, event=None, callback=None):
        for element in self.elements.values():
            element.unsubscribe()
        Events.Unsubscribe(callback_id=callback_id, event=event, callback=callback, caller_id=self)

    def set_enabled(self, enabled):
        self.enabled = enabled

    def trace_save(self, var, callback):
        if self.var is not None and self.var != var:
            raise ValueError(f'Cannot trace multiple vars at the same time!')
        self.var = var
        if (hasattr(self, 'set') and callback == self.set) or callback == self.show or callback == self.set_tooltip or callback == self.set_enabled:
            callback(var.get())
            Vars.Settings.subscribe_on_save(var, lambda traced_var, value, _: callback(value), caller_id=self)
        else:
            callback(var, var.get(), None)
            Vars.Settings.subscribe_on_save(var, callback, caller_id=self)

    def trace_write(self, var, callback):
        if self.var is not None and self.var != var:
            raise ValueError(f'Cannot trace multiple vars at the same time!')
        self.var = var
        if callback == self.set or callback == self.show or callback == self.set_tooltip or callback == self.set_enabled:
            callback(var.get())
            Vars.Settings.subscribe_on_write(var, lambda traced_var, value: callback(value), caller_id=self)
        else:
            callback(var, var.get())
            Vars.Settings.subscribe_on_write(var, callback, caller_id=self)

    def untrace_save(self, callback_id=None, var=None, callback=None):
        for element in self.elements.values():
            element.untrace_save()
        Vars.Settings.unsubscribe_on_save(callback_id=callback_id, var=var, callback=callback, caller_id=self)
        self.var = None

    def untrace_write(self, callback_id=None, var=None, callback=None):
        for element in self.elements.values():
            element.untrace_write()
        Vars.Settings.unsubscribe_on_write(callback_id=callback_id, var=var, callback=callback, caller_id=self)
        self.var = None

    def hide(self, hide=True):
        if hide or not self.enabled:
            self.is_hidden = True

            for element in self.elements.values():
                element.hide()
            self._hide()
        else:
            self.show()

    def _hide(self):
        raise NotImplementedError

    def show(self, show=True):
        if show and self.enabled:
            self.is_hidden = False

            for element in self.elements.values():
                element.show()
            self._show()
        else:
            self.hide()

    def destroy(self):
        try:
            self.tooltip.destroy()
        except:
            pass
        super().destroy()

    def _show(self):
        raise NotImplementedError

    def set_tooltip(self, text='', **kwargs):
        if self.tooltip is None:
            self.tooltip = UIToolTip(self, msg=text, **kwargs)
        else:
            self.tooltip.msg = text

    def get_resource_path(self, resource_path: str = ''):
        return self.master.get_resource_path()


class UIElementBase(UIElement):
    def __init__(self, **kwargs):
        UIElement.__init__(self, **kwargs)
        self.manager = None
        self.last_place = None
        self.last_pack = None

    def _hide(self):
        if self.get_manager(last_used=True) == 'grid':
            self.grid_remove()
        elif self.get_manager(last_used=True) == 'place':
            self.place_forget()
        elif self.get_manager(last_used=True) == 'pack':
            self.pack_forget()

    def _show(self):
        if self.get_manager(last_used=True) == 'grid':
            self.grid()
        elif self.get_manager(last_used=True) == 'place':
            self.place()
        elif self.get_manager(last_used=True) == 'pack':
            self.pack()

    def get_manager(self, last_used=False):
        if last_used:
            return self.manager
        else:
            return self.winfo_manager()

    def grid(self, **kwargs):
        self.manager = 'grid'
        super().grid(**kwargs)

    def place(self, **kwargs):
        self.manager = 'place'
        if self.last_place:
            super().place(**self.last_place)
        else:
            self.last_place = kwargs
            super().place(**kwargs)

    def pack(self, **kwargs):
        self.manager = 'pack'
        if self.last_pack:
            super().pack(**self.last_pack)
        else:
            self.last_pack = kwargs
            super().pack(**kwargs)

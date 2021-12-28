# 3DMousePlus: A Blender Addon for transforming objects with a 3DConnexion mouse
# Copyright (C) 2021  Spencer Killen
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from os import pipe, write
from select import select
from threading import Thread
from time import sleep
from typing import List, Union

from .spnav import (
    spnav_open,
    spnav_close,
    spnav_fd,
    spnav_poll_event,
    SpnavButtonEvent,
    SpnavMotionEvent,
)


class SpnavListener:
    def __init__(self):
        rx, self.__tx = pipe()
        self.__motion_events: List[SpnavMotionEvent] = None
        self.__button_events: List[SpnavButtonEvent] = None
        self.__thread = Thread(target=self.__run_thread, args=(rx,))
        self.__thread.start()

    def activate_motion(self):
        if self.__motion_events is None:
            self.__motion_events = []

    def activate_button(self):
        if self.__button_events is None:
            self.__button_events = []

    def deactivate_motion(self):
        self.__motion_events = None

    def deactivate_button(self):
        self.__button_events = None

    def motion_events(self):
        consumed = tuple(self.__motion_events)
        self.__motion_events.clear()
        return consumed

    def button_events(self):
        consumed = tuple(self.__button_events)
        self.__button_events.clear()
        return consumed

    def kill(self):
        write(self.__tx, b"Die!")
        self.__thread.join()

    def __run_thread(self, killed: int):
        spnav_open()
        new_event: int = spnav_fd()
        assert spnav_fd != -1, "spnav_fd failed"
        while True:
            r, *_ = select((killed, new_event), [], [])
            if killed in r:
                break
            elif new_event in r:
                event = spnav_poll_event()
                assert event is not None, "Why wasn't there an event?"
                while event is not None:
                    if isinstance(event, SpnavButtonEvent):
                        if self.__button_events is not None:
                            self.__button_events.append(event)
                    elif isinstance(event, SpnavMotionEvent):
                        if self.__motion_events is not None:
                            self.__motion_events.append(event)
                    event = spnav_poll_event()
        spnav_close()

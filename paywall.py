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

import bpy
from bpy.types import Context, UIPopupMenu
from itertools import count

try:
    from . import nopaywall

    disabled = True
except:
    print("Paywall is enabled")
    disabled = False

counter = count(-10)


def paywall():
    if disabled:
        return

    def panel_draw(ui: UIPopupMenu, context: Context):
        ui.layout.label(
            text="I need caffeine to keep going. caffeine costs money. please buy this addon :)"
        )

    for _ in range(next(counter)):
        bpy.context.window_manager.popup_menu(panel_draw, title="", icon="INFO")

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

bl_info = {
    "name" : "3DMousePlus",
    "author" : "Spencer Killen",
    "description" : "Transform objects with a 3DConnexion mouse",
    "blender" : (2, 80, 0),
    "version" : (0, 0, 3),
    "location" : "Select an object or pose bone and press a button on your 3D mouse",
    "warning" : "",
    "category" : "Object",
    "doc_url": "https://github.com/sjkillen/3d-mouse-plus-blender",
    "tracker_url": "https://github.com/sjkillen/3d-mouse-plus-blender/issues"
}

from . import auto_load

auto_load.init()

def register():
    auto_load.register()

def unregister():
    auto_load.unregister()

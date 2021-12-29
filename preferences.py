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
from bpy.types import AddonPreferences, Context, SpaceView3D
from bpy.props import BoolProperty, FloatProperty
from .listener import SpnavMotionEvent
from mathutils import Euler, Matrix, Vector


class Addon3DMousePlusPreferences(AddonPreferences):
    bl_idname = __package__
    sensitivity_rotate: FloatProperty(
        name="Rotation sensitivity", min=0.0, soft_max=2.0, default=0.5
    )
    sensitivity_translation: FloatProperty(
        name="Translation sensitivity",
        min=0.0,
        soft_max=0.01,
        default=0.005,
        precision=4,
    )
    use_view_axis_x: BoolProperty(
        "Use View Axes X",
        description="If enabled, the X axis is relative to the 3D viewport instead of the global axes",
        default=True,
        options=set(),
    )
    use_view_axis_y: BoolProperty(
        "Use View Axes Y",
        description="If enabled, the Y axis is relative to the 3D viewport instead of the global axes",
        default=True,
        options=set(),
    )
    use_view_axis_z: BoolProperty(
        "Use View Axes Z",
        description="If enabled, the Z axis is relative to the 3D viewport instead of the global axes",
        default=True,
        options=set(),
    )
    translation_invert_x: BoolProperty(
        "Translation Invert X", default=False, options=set()
    )
    translation_invert_y: BoolProperty(
        "Translation Invert Y", default=False, options=set()
    )
    translation_invert_z: BoolProperty(
        "Translation Invert Z", default=False, options=set()
    )
    translation_flip_x_y: BoolProperty(
        "Translation Flip X and Y", default=False, options=set()
    )
    translation_flip_x_z: BoolProperty(
        "Translation Flip X and Z", default=False, options=set()
    )
    translation_flip_y_z: BoolProperty(
        "Translation Flip Y and Z", default=False, options=set()
    )
    rotate_invert_x: BoolProperty("Rotate Invert X", default=False, options=set())
    rotate_invert_y: BoolProperty("Rotate Invert Y", default=False, options=set())
    rotate_invert_z: BoolProperty("Rotate Invert Z", default=False, options=set())
    rotate_flip_x_y: BoolProperty("Rotate Flip X and Y", default=False, options=set())
    rotate_flip_x_z: BoolProperty("Rotate Flip X and Z", default=False, options=set())
    rotate_flip_y_z: BoolProperty("Rotate Flip Y and Z", default=False, options=set())

    def draw(self, context: Context):
        row = self.layout.row(heading="Use View Axes")
        for axis in "xyz":
            row.prop(self, f"use_view_axis_{axis}", text=axis.upper())
        row = self.layout.row(heading="Sensitivity")
        row.prop(self, "sensitivity_translation", text="Translation")
        row.prop(self, "sensitivity_rotate", text="Rotation")
        for t in ("translation", "rotate"):
            row = self.layout.row(heading=(f"{t.title()} Invert"))
            for axis in "xyz":
                prop = f"{t}_invert_{axis}"
                row.prop(self, prop, text=f"{axis.title()}")
            row = self.layout.row(heading=(f"{t.title()} Flip"))
            for axes in ("xy", "xz", "yz"):
                prop = f"{t}_flip_{axes[0]}_{axes[1]}"
                axes = " and ".join(axes.upper())
                row.prop(self, prop, text=f"{axes}")


def get_prefs() -> Addon3DMousePlusPreferences:
    prefs = bpy.context.preferences
    prefs: Addon3DMousePlusPreferences = prefs.addons[__package__].preferences
    return prefs


def get_preferred_active_view_rotation_matrix() -> Matrix:
    if bpy.context.area is None:
        return None
    spaceview3d: SpaceView3D = next(
        (space for space in bpy.context.area.spaces if isinstance(space, SpaceView3D)),
        None,
    )
    if spaceview3d is None or spaceview3d.region_3d is None:
        return None
    matrix = Matrix(spaceview3d.region_3d.view_matrix)
    matrix.translation = Vector()
    angle: Euler = matrix.to_euler()
    identity_angle = Matrix().to_euler()
    prefs = get_prefs()
    angle.x = angle.x if prefs.use_view_axis_x else identity_angle.x
    angle.y = angle.y if prefs.use_view_axis_y else identity_angle.y
    angle.z = angle.z if prefs.use_view_axis_z else identity_angle.z
    matrix = angle.to_matrix().to_4x4()
    return matrix


def apply_event_preferences(event: SpnavMotionEvent) -> SpnavMotionEvent:
    prefs = get_prefs()
    loc = list(event.translation)
    rot = list(event.rotation)

    for t, vec in (("translation", loc), ("rotate", rot)):
        sensitivity = getattr(prefs, f"sensitivity_{t}")
        for i, x in enumerate(vec):
            vec[i] = x * sensitivity
        for axis in "xyz":
            prop = f"{t}_invert_{axis}"
            index = "xyz".index(axis)
            if getattr(prefs, prop):
                vec[index] *= -1
        for axes in ("xy", "xz", "yz"):
            indices = tuple("xyz".index(axis) for axis in axes)
            prop = f"{t}_flip_{axes[0]}_{axes[1]}"
            if getattr(prefs, prop):
                vec[indices[0]], vec[indices[1]] = vec[indices[1]], vec[indices[0]]

    return SpnavMotionEvent(loc, rot, event.period)

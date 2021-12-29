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

"""
An operator to consume events from the listener module and transform objects accordingly
Although the listener module is capable of polling events without blocking,
we listen for NDOF events here because its not safe for the listener module cannot touch blender structures
(See https://docs.blender.org/api/current/info_gotcha.html#strange-errors-when-using-the-threading-module)
and this gives us a method of gaurenteeing safety.

Ideas: fixed rotation mode instead of using delta
"""


import bpy
from mathutils import Euler, Matrix, Vector
from typing import Set, Tuple, Union
from bpy.types import Context, Event, Object, SpaceView3D
from bpy.props import BoolProperty, FloatProperty, StringProperty

from .listener import SpnavListener

ERROR_MSG = "You must select a single object"


class NDOFTransformOperator(bpy.types.Operator):
    bl_idname = "wm.ndoftransform"
    bl_label = "NDOFTransform"
    bl_options = {"REGISTER", "UNDO"}

    btn: StringProperty(
        description="The button that was used to start operation", default="NONE"
    )
    sensitivity_rotate: FloatProperty(
        name="Rotation sensitivity", min=0.0, soft_max=2.0, default=0.5
    )
    sensitivity_translate: FloatProperty(
        name="Translation sensitivity",
        min=0.0,
        soft_max=0.01,
        default=0.005,
        precision=4,
    )
    locked_rotate: BoolProperty("Lock rotation", default=False)
    locked_translate: BoolProperty("Lock translation", default=False)
    bend_mode: BoolProperty("Bend Mode", default=False)

    def __init__(self):
        self.initial_transform = None

    @classmethod
    def poll(cls, context: Context):
        if len(context.selected_objects) != 1:
            NDOFTransformOperator.poll_message_set(ERROR_MSG)
            return False
        return True

    def execute(self, context) -> Union[Set[int], Set[str]]:
        spnav_listener.activate_motion()
        return {"FINISHED"}

    def check_button_event(self, context: Context, event: Event):
        if event is None:
            return
        if event.type == "NDOF_BUTTON_MENU" or event.type == "NDOF_BUTTON_FIT":
            self.btn = event.type
        else:
            self.btn = "NONE"

    def get_bent_rotate_sensitivity(self):
        mod = 16
        return self.sensitivity_rotate * (mod if self.bend_mode else 1)

    def get_bent_translate_sensitivity(self):
        mod = 8
        return self.sensitivity_translate * (mod if self.bend_mode else 1)

    def get_active_view_rotation_matrix(self, context: Context) -> Matrix:
        if context.area is None:
            return None
        spaceview3d: SpaceView3D = next(
            (space for space in context.area.spaces if isinstance(space, SpaceView3D)),
            None,
        )
        if spaceview3d is None or spaceview3d.region_3d is None:
            return None
        matrix = Matrix(spaceview3d.region_3d.view_matrix)
        matrix.translation = Vector()
        return matrix

    def invoke(self, context: Context, event: Event) -> Union[Set[int], Set[str]]:

        if not NDOFTransformOperator.poll(context):
            self.report({"ERROR"}, ERROR_MSG)
            return {"FINISHED"}

        if self.btn == "NDOF_BUTTON_FIT":
            self.init_locks()
        else:
            self.reset_locks()

        self.check_button_event(context, event)
        context.window_manager.modal_handler_add(self)
        target: Object = context.selected_objects[0]
        self.execute(context)
        return {"RUNNING_MODAL"}

    def update_target_matrix(self, target: Object, new_matrix: Matrix):
        "Respect the target object's transform locks"
        rot = Euler(
            x if not l else old
            for x, old, l in zip(
                new_matrix.to_euler(),
                target.matrix_basis.to_euler(),
                target.lock_rotation,
            )
        )
        loc = Vector(
            x if not l else old
            for x, old, l in zip(
                new_matrix.translation,
                target.matrix_basis.translation,
                target.lock_location,
            ) 
        )
        m = rot.to_matrix().to_4x4()
        m.translation = loc
        target.matrix_basis = m

    def rotate_target(self, view: Matrix, target: Object, rot: Tuple[int, int, int]):
        rot = rot[0], rot[1], -rot[2]
        sensitivity = self.get_bent_rotate_sensitivity()
        world = Matrix(target.matrix_basis).copy()
        rot = Euler(x / 500 * sensitivity for x in rot).to_matrix().to_4x4()
        world_centered = world.copy()
        world_centered.translation = Vector()
        a: Matrix = (view.inverted_safe() @ (rot @ view)) @ world_centered
        a.translation = world.translation
        self.update_target_matrix(target, a)

    def translate_target(self, view: Matrix, target: Object, loc: Tuple[int, int, int]):
        loc = loc[0], loc[2], loc[1]
        sensitivity = self.get_bent_translate_sensitivity()
        move = Matrix()
        move.translation = Vector(x * sensitivity for x in loc)
        world_pos = Matrix()
        world_pos.translation = target.location
        a: Matrix = view.inverted_safe() @ (move @ (view @ world_pos))
        world = Matrix(target.matrix_basis).copy()
        world.translation = a.translation
        self.update_target_matrix(target, world)

    def end_modal(self, context: Context, undo: bool):
        spnav_listener.deactivate_motion()
        return {"FINISHED"}

    def init_locks(self):
        self.locked_translate = True
        self.locked_rotate = False

    def reset_locks(self):
        self.locked_rotate = False
        self.locked_translate = False

    def flip_locks(self):
        self.locked_rotate, self.locked_translate = (
            self.locked_translate,
            self.locked_rotate,
        )
        if self.locked_translate == self.locked_rotate:
            self.init_locks()

    def kb_events(self, context: Context, event: Event) -> Union[Set[int], Set[str]]:
        if event.type in (
            "ESC",
            "RIGHTMOUSE",
            "LEFTMOUSE",
            "RET",
        ):
            should_undo = event.type not in ("RET", "LEFTMOUSE")
            return self.end_modal(context, should_undo)
        if event.type == "NDOF_BUTTON_FIT" and event.value == "RELEASE":
            self.flip_locks()
        if event.type == "NDOF_BUTTON_MENU" and event.value == "RELEASE":
            self.reset_locks()
        if event.type == "SPACE" and event.value == "RELEASE":
            self.toggle_bend_mode()
        return None

    def toggle_bend_mode(self):
        if self.bend_mode:
            self.initial_transform = None
        self.bend_mode = not self.bend_mode

    def check_bend_mode(self, target: Object):
        if not self.bend_mode:
            return
        if self.initial_transform is None:
            self.initial_transform = target.matrix_basis.copy()
        else:
            target.matrix_basis = self.initial_transform

    def modal(self, context: Context, event: Event) -> Union[Set[int], Set[str]]:

        if should_return := self.kb_events(context, event):
            return should_return

        target = context.selected_objects[0]
        if context.selected_pose_bones:
            target = context.selected_pose_bones[0]

        for mo in spnav_listener.motion_events():
            view = self.get_active_view_rotation_matrix(context)
            self.check_bend_mode(target)
            if not self.locked_rotate:
                self.rotate_target(view, target, mo.rotation)
            if not self.locked_translate:
                self.translate_target(view, target, mo.translation)

        return {"RUNNING_MODAL"}


def ndof_transform_menu(self, context: Context):
    self.layout.operator(NDOFTransformOperator.bl_idname, text="Enable NDOF Transform")


spnav_listener: SpnavListener = None
addon_keymaps = []


def register():
    global spnav_listener
    spnav_listener = SpnavListener()
    # Add operator to search
    bpy.types.VIEW3D_MT_view.append(ndof_transform_menu)
    addon_kc = bpy.context.window_manager.keyconfigs.addon
    if addon_kc is not None:
        for mode in ("Pose", "Object Mode"):
            km = addon_kc.keymaps.new(name=f"{mode}", space_type="EMPTY")
            kmi1 = km.keymap_items.new(
                NDOFTransformOperator.bl_idname, type="NDOF_BUTTON_MENU", value="ANY"
            )
            kmi2 = km.keymap_items.new(
                NDOFTransformOperator.bl_idname,
                type="NDOF_BUTTON_FIT",
                value="ANY",
            )
            addon_keymaps.append((km, (kmi1, kmi2)))


def unregister():
    global spnav_listener
    spnav_listener.kill()
    spnav_listener = None
    bpy.types.VIEW3D_MT_view.remove(ndof_transform_menu)

    # Don't know if this is really neccessary but this is what they do in the docs tutorial...
    for km, kmis in addon_keymaps:
        for kmi in kmis:
            km.keymap_items.remove(kmi)
        bpy.context.window_manager.keyconfigs.addon.keymaps.remove(km)
    addon_keymaps.clear()

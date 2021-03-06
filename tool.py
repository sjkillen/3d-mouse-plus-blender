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
from mathutils import Euler, Matrix, Vector
from typing import Set, Union
from bpy.types import Context, Event, Object
from bpy.props import BoolProperty, StringProperty
from .spnav import SpnavMotionEvent
from .matrix_memo import MatrixMemo

from .preferences import (
    get_preferred_active_view_rotation_matrix,
    apply_event_preferences,
)
from .listener import SpnavListener

ERROR_MSG = "You must select a single object"
BENT_ROTATE_MOD = 16
BENT_TRANSLATE_MOD = 8


class NDOFTransformOperator(bpy.types.Operator):
    bl_idname = "wm.ndoftransform"
    bl_label = "Activate 3DMousePlus Mode"

    btn: StringProperty(
        description="The button that was used to start operation", default="NONE"
    )
    locked_rotate: BoolProperty("Lock rotation", default=False)
    locked_translate: BoolProperty("Lock translation", default=False)
    bend_mode: BoolProperty("Bend Mode", default=False)

    def __init__(self):
        self.initial_transform = None
        self.bend_transform = None
        self.finished = False
        self.mouse_at_rest = False
        self.should_undo = False

    @classmethod
    def poll(cls, context: Context):
        if len(context.selected_objects) != 1:
            NDOFTransformOperator.poll_message_set(ERROR_MSG)
            return False
        return True

    def execute(self, context) -> Union[Set[int], Set[str]]:
        spnav_listener.activate_motion()
        self.bend_transform = None
        self.initial_transform = None
        return {"FINISHED"}

    def check_button_event(self, context: Context, event: Event):
        if event is None:
            return
        if event.type == "NDOF_BUTTON_MENU" or event.type == "NDOF_BUTTON_FIT":
            self.btn = event.type
        else:
            self.btn = "NONE"

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
        self.execute(context)
        return {"RUNNING_MODAL"}

    def update_target_matrix(
        self, target: Object, new_matrix: Matrix, memo: MatrixMemo
    ):
        "Respect the target object's transform locks"
        loc = Vector(
            x if not l else old
            for x, old, l in zip(
                new_matrix.translation,
                memo.get_matrix().translation,
                target.lock_location,
            )
        )
        rot = Euler(
            x if not l else old
            for x, old, l in zip(
                new_matrix.to_euler(),
                memo.get_matrix().to_euler(),
                target.lock_rotation,
            )
        )
        scale = Vector(target.scale)
        memo.set_matrix(Matrix.LocRotScale(loc, rot, scale))

    def rotate_target(self, view: Matrix, target: Object, rot, memo: MatrixMemo):
        rot = rot[0], rot[1], -rot[2]
        mod = BENT_ROTATE_MOD if self.bend_mode else 1
        world = Matrix(memo.get_matrix()).copy()
        rot = Euler(x / 500 * mod for x in rot).to_matrix().to_4x4()
        world_centered = world.copy()
        world_centered.translation = Vector()
        a: Matrix = (view.inverted_safe() @ (rot @ view)) @ world_centered
        a.translation = world.translation
        self.update_target_matrix(target, a, memo)

    def translate_target(self, view: Matrix, target: Object, loc, memo: MatrixMemo):
        loc = loc[0], loc[2], loc[1]
        mod = BENT_TRANSLATE_MOD if self.bend_mode else 1
        move = Matrix()
        move.translation = Vector(x * mod for x in loc)
        world_pos = Matrix()
        world_pos.translation = target.location
        a: Matrix = view.inverted_safe() @ (move @ (view @ world_pos))
        world = Matrix(memo.get_matrix()).copy()
        world.translation = a.translation
        self.update_target_matrix(target, world, memo)

    def end_modal(self, memo: MatrixMemo):
        from .paywall import paywall

        if self.should_undo:
            memo.set_matrix(self.initial_transform)
        self.finished = False
        self.mouse_at_rest = False
        self.initial_transform = None
        self.should_undo = False
        self.bend_transform = None
        paywall()
        spnav_listener.deactivate_motion()
        return {"FINISHED"}

    def finish(self):
        self.finished = True

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

    def kb_events(self, event: Event):
        if event.type in (
            "ESC",
            "RIGHTMOUSE",
            "LEFTMOUSE",
            "RET",
        ):
            self.should_undo = event.type not in ("RET", "LEFTMOUSE")
            self.finish()
        elif event.type == self.get_kb(ToggleModeLock) and event.value == "RELEASE":
            self.flip_locks()
        elif event.type == self.get_kb(ResetModeLock) and event.value == "RELEASE":
            self.reset_locks()
        elif event.type == self.get_kb(ToggleBend) and event.value == "RELEASE":
            self.toggle_bend_mode()

    def toggle_bend_mode(self):
        if self.bend_mode:
            self.bend_transform = None
        self.bend_mode = not self.bend_mode

    def check_bend_mode(self, memo: MatrixMemo):
        if not self.bend_mode:
            return
        if self.bend_transform is None:
            self.bend_transform = memo.get_matrix()
        else:
            memo.set_matrix(self.bend_transform)

    def check_mouse_at_rest(self, ev: SpnavMotionEvent):
        self.mouse_at_rest = all(x == 0 for x in (*ev.translation, *ev.rotation))
        return self.mouse_at_rest

    def get_kb(self, operator) -> str:
        km = bpy.context.window_manager.keyconfigs.user.keymaps["Object Mode"]
        kb =  km.keymap_items.find_from_operator(operator.bl_idname).type
        return kb

    def modal(self, context: Context, event: Event) -> Union[Set[int], Set[str]]:
        target = context.selected_objects[0]
        if context.selected_pose_bones:
            target = context.selected_pose_bones[0]
        memo = MatrixMemo(target)
        if self.initial_transform is None:
            self.initial_transform = memo.get_matrix()

        self.kb_events(event)
        if self.finished and self.mouse_at_rest:
            return self.end_modal(memo)

        for mo in spnav_listener.motion_events():
            if (resting := self.check_mouse_at_rest(mo)) or self.finished:
                if self.finished and resting:
                    return self.end_modal(memo)
                else:
                    continue
            view = get_preferred_active_view_rotation_matrix()
            mo = apply_event_preferences(mo)
            self.check_bend_mode(memo)
            if context.mode == "POSE" or not self.locked_rotate:
                self.rotate_target(view, target, mo.rotation, memo)
            if context.mode != "POSE" and not self.locked_translate:
                self.translate_target(view, target, mo.translation, memo)

        return {"RUNNING_MODAL"}


def ndof_transform_menu(self, context: Context):
    self.layout.operator(NDOFTransformOperator.bl_idname, text="Enable NDOF Transform")


class ToggleModeLock(bpy.types.Operator):
    bl_idname = "object.ndoftransformtogglemodelock"
    bl_label = "3DMousePlus: Toggle Rotation/Translation"

    def execute(self, context):
        return {"FINISHED"}


class ResetModeLock(bpy.types.Operator):
    bl_idname = "object.ndoftransformresetmodelock"
    bl_label = "3DMousePlus: Reset Rotation/Translation Lock"

    def execute(self, context):
        return {"FINISHED"}


class ToggleBend(bpy.types.Operator):
    bl_idname = "object.ndoftransformtogglebendmode"
    bl_label = "3DMousePlus: Toggle Bend Mode"

    def execute(self, context):
        return {"FINISHED"}


spnav_listener: SpnavListener = None
addon_keymaps = []


def register():
    global spnav_listener
    spnav_listener = SpnavListener()
    # Add operator to search
    bpy.types.VIEW3D_MT_view.append(ndof_transform_menu)
    addon_kc = bpy.context.window_manager.keyconfigs.addon
    if addon_kc is None:
        return
    for mode in ("Pose", "Object Mode"):
        km = addon_kc.keymaps.new(name=mode, space_type="EMPTY")
        buttons = ("MENU", "FIT", "1", "2")
        kmis = tuple(
            km.keymap_items.new(
                NDOFTransformOperator.bl_idname,
                type=f"NDOF_BUTTON_{button}",
                value="ANY",
            )
            for button in buttons
        )
        addon_keymaps.append((km, kmis))


    km = addon_kc.keymaps.new(name="Object Mode", space_type="EMPTY")

    km.keymap_items.new(
        ToggleModeLock.bl_idname,
        type="NDOF_BUTTON_FIT",
        value="ANY",
    )
    km.keymap_items.new(
        ResetModeLock.bl_idname,
        type="NDOF_BUTTON_MENU",
        value="ANY",
    )
    km.keymap_items.new(
        ToggleBend.bl_idname,
        type="SPACE",
        value="ANY",
    )


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

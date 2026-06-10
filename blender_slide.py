# Blender Slide - present collections as slides in Blender.
# Copyright (C) 2026 Naga
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

bl_info = {
    "name": "Blender Slide",
    "author": "Naga",
    "version": (1, 6, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar (N) > Blender Slide",
    "description": "Present registered collections as slides in Blender",
    "doc_url": "https://github.com/40258jump-design/blender-slide",
    "tracker_url": "https://github.com/40258jump-design/blender-slide/issues",
    "category": "3D View",
}

import bpy


# ============================================================
# Core: show only the current slide, hide the others
# ============================================================
def _find_layer_collection(view_layer, target_coll):
    """Recursively find the LayerCollection that wraps the given Collection
    (matched by identity)."""
    def rec(lc):
        if lc.collection == target_coll:
            return lc
        for ch in lc.children:
            r = rec(ch)
            if r:
                return r
        return None

    return rec(view_layer.layer_collection)


def _restore_collection(context, coll):
    """Restore normal visibility when a collection leaves slide management."""
    if coll is None:
        return

    lc = _find_layer_collection(context.view_layer, coll)
    if lc:
        lc.exclude = False
        lc.hide_viewport = False


def apply_slide_visibility(context):
    """Show only the current slide according to the switch method."""
    props = context.scene.blender_slide
    slides = props.slides

    if not slides:
        return

    idx = max(0, min(props.active_index, len(slides) - 1))
    method = props.switch_method
    view_layer = context.view_layer

    for i, item in enumerate(slides):
        coll = item.collection
        if coll is None:
            continue

        lc = _find_layer_collection(view_layer, coll)
        if lc is None:
            continue

        is_current = (i == idx)

        if method == 'EXCLUDE':
            lc.hide_viewport = False
            lc.exclude = not is_current
        else:
            lc.exclude = False
            lc.hide_viewport = not is_current


# ============================================================
# Properties
# ============================================================
def _on_index_update(self, context):
    apply_slide_visibility(context)


def _on_method_update(self, context):
    apply_slide_visibility(context)


class BS_SlideItem(bpy.types.PropertyGroup):
    collection: bpy.props.PointerProperty(
        name="Collection",
        type=bpy.types.Collection,
    )


class BS_Props(bpy.types.PropertyGroup):
    slides: bpy.props.CollectionProperty(type=BS_SlideItem)

    active_index: bpy.props.IntProperty(
        default=0,
        min=0,
        update=_on_index_update,
    )

    switch_method: bpy.props.EnumProperty(
        name="Switch Method",
        items=[
            ('EXCLUDE', "Exclude",
             "Exclude from the view layer (lightweight, affects renders)"),
            ('HIDE', "Hide",
             "Hide in the viewport only (does not affect renders)"),
        ],
        default='EXCLUDE',
        update=_on_method_update,
    )

    start_frame: bpy.props.IntProperty(
        name="Start Frame",
        description="Frame to jump to when pressing \"Back to Start\"",
        default=1,
    )


# ============================================================
# UIList: slide list
# ============================================================
class BS_UL_slides(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_propname, index):
        props = context.scene.blender_slide

        row = layout.row(align=True)
        row.label(text="", icon='PLAY' if index == props.active_index else 'BLANK1')

        coll = item.collection
        if coll is not None:
            row.label(
                text="%d. %s" % (index + 1, coll.name),
                icon='OUTLINER_COLLECTION',
            )
        else:
            row.label(
                text="%d. (missing)" % (index + 1),
                icon='ERROR',
            )


# ============================================================
# Operators
# ============================================================
class BS_OT_add(bpy.types.Operator):
    bl_idname = "blender_slide.add"
    bl_label = "Add"
    bl_description = "Add the active collection as a slide"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.blender_slide
        active_coll = context.view_layer.active_layer_collection.collection

        if active_coll is None or active_coll == context.scene.collection:
            self.report({'WARNING'}, "Make the collection you want to add active")
            return {'CANCELLED'}

        if any(s.collection == active_coll for s in props.slides):
            self.report({'INFO'}, "\"%s\" is already registered" % active_coll.name)
            return {'CANCELLED'}

        item = props.slides.add()
        item.collection = active_coll
        props.active_index = len(props.slides) - 1

        self.report({'INFO'}, "Added \"%s\"" % active_coll.name)
        return {'FINISHED'}


class BS_OT_remove(bpy.types.Operator):
    bl_idname = "blender_slide.remove"
    bl_label = "Remove"
    bl_description = "Remove the selected slide from the list"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.blender_slide

        if not props.slides:
            return {'CANCELLED'}

        idx = max(0, min(props.active_index, len(props.slides) - 1))

        _restore_collection(context, props.slides[idx].collection)
        props.slides.remove(idx)

        if props.slides:
            props.active_index = min(idx, len(props.slides) - 1)
        else:
            props.active_index = 0

        apply_slide_visibility(context)
        return {'FINISHED'}


class BS_OT_move(bpy.types.Operator):
    bl_idname = "blender_slide.move"
    bl_label = "Move"
    bl_description = "Move the slide up or down in the list"
    bl_options = {'REGISTER', 'UNDO'}

    direction: bpy.props.EnumProperty(
        items=[
            ('UP', "Up", ""),
            ('DOWN', "Down", ""),
        ]
    )

    def execute(self, context):
        props = context.scene.blender_slide
        n = len(props.slides)

        if n < 2:
            return {'CANCELLED'}

        idx = max(0, min(props.active_index, n - 1))
        new = idx - 1 if self.direction == 'UP' else idx + 1

        if new < 0 or new >= n:
            return {'CANCELLED'}

        props.slides.move(idx, new)
        props.active_index = new

        return {'FINISHED'}


class BS_OT_next(bpy.types.Operator):
    bl_idname = "blender_slide.next"
    bl_label = "Next"
    bl_description = "Go to the next slide"

    def execute(self, context):
        props = context.scene.blender_slide

        if not props.slides:
            return {'CANCELLED'}

        props.active_index = (props.active_index + 1) % len(props.slides)
        return {'FINISHED'}


class BS_OT_prev(bpy.types.Operator):
    bl_idname = "blender_slide.prev"
    bl_label = "Previous"
    bl_description = "Go to the previous slide"

    def execute(self, context):
        props = context.scene.blender_slide

        if not props.slides:
            return {'CANCELLED'}

        props.active_index = (props.active_index - 1) % len(props.slides)
        return {'FINISHED'}


class BS_OT_reset(bpy.types.Operator):
    bl_idname = "blender_slide.reset"
    bl_label = "Back to Start"
    bl_description = "Return to the first slide and jump to the start frame"

    def execute(self, context):
        props = context.scene.blender_slide

        context.scene.frame_set(props.start_frame)

        if not props.slides:
            return {'FINISHED'}

        if props.active_index == 0:
            apply_slide_visibility(context)
        else:
            props.active_index = 0

        return {'FINISHED'}


class BS_OT_refresh(bpy.types.Operator):
    bl_idname = "blender_slide.refresh"
    bl_label = "Reapply Visibility"
    bl_description = ("Reapply the current slide's visibility "
                      "(recover after manual Outliner changes)")

    def execute(self, context):
        apply_slide_visibility(context)
        return {'FINISHED'}


class BS_OT_clean(bpy.types.Operator):
    bl_idname = "blender_slide.clean"
    bl_label = "Remove Invalid Slides"
    bl_description = "Remove slides whose collections have been deleted"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.blender_slide
        removed = 0

        for i in range(len(props.slides) - 1, -1, -1):
            if props.slides[i].collection is None:
                props.slides.remove(i)
                removed += 1

        if props.slides:
            props.active_index = min(props.active_index, len(props.slides) - 1)
        else:
            props.active_index = 0

        if removed:
            self.report({'INFO'}, "Removed %d invalid slide(s)" % removed)
        else:
            self.report({'INFO'}, "Nothing to remove")

        apply_slide_visibility(context)
        return {'FINISHED'}


class BS_OT_play_anim(bpy.types.Operator):
    bl_idname = "blender_slide.play_anim"
    bl_label = "Play / Pause Animation"
    bl_description = "Toggle timeline playback"

    def execute(self, context):
        bpy.ops.screen.animation_play()
        return {'FINISHED'}


class BS_OT_make_workspace(bpy.types.Operator):
    bl_idname = "blender_slide.make_workspace"
    bl_label = "Presentation Workspace"
    bl_description = ("Create a presentation workspace "
                      "(camera view with UI hidden)")

    WS_NAME = "Presentation"

    def execute(self, context):
        existing = bpy.data.workspaces.get(self.WS_NAME)

        if existing:
            context.window.workspace = existing
            self.report({'INFO'}, "Switched to the existing Presentation workspace")
            return {'FINISHED'}

        bpy.ops.workspace.duplicate()
        ws = context.window.workspace
        ws.name = self.WS_NAME

        configured = False

        for screen in ws.screens:
            for area in screen.areas:
                if area.type != 'VIEW_3D':
                    continue

                for space in area.spaces:
                    if space.type != 'VIEW_3D':
                        continue

                    if space.region_3d:
                        space.region_3d.view_perspective = 'CAMERA'

                    space.overlay.show_overlays = False
                    space.show_gizmo = False
                    space.show_region_header = False
                    space.show_region_ui = False
                    space.show_region_toolbar = False
                    configured = True

        if not configured:
            self.report({'WARNING'}, "No 3D Viewport found")
        else:
            self.report({'INFO'}, "Created the \"Presentation\" workspace")

        return {'FINISHED'}


# ============================================================
# Panel (N sidebar)
# ============================================================
class BS_PT_panel(bpy.types.Panel):
    bl_label = "Blender Slide"
    bl_idname = "BS_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Blender Slide"

    def draw(self, context):
        layout = self.layout
        props = context.scene.blender_slide

        layout.label(text="Slides", icon='SEQUENCE')

        row = layout.row()
        row.template_list(
            "BS_UL_slides",
            "",
            props,
            "slides",
            props,
            "active_index",
            rows=5,
        )

        col = row.column(align=True)
        col.operator("blender_slide.add", text="", icon='ADD')
        col.operator("blender_slide.remove", text="", icon='REMOVE')
        col.separator()
        col.operator("blender_slide.move", text="", icon='TRIA_UP').direction = 'UP'
        col.operator("blender_slide.move", text="", icon='TRIA_DOWN').direction = 'DOWN'

        box = layout.box()
        n = len(props.slides)
        cur = (props.active_index + 1) if n else 0

        header = box.row(align=True)
        header.label(text="Current: %d / %d" % (cur, n))
        header.operator("blender_slide.refresh", text="", icon='FILE_REFRESH')

        nav = box.row(align=True)
        nav.operator("blender_slide.prev", text="Prev", icon='TRIA_LEFT')
        nav.operator("blender_slide.next", text="Next", icon='TRIA_RIGHT')

        reset_row = box.row(align=True)
        reset_row.operator("blender_slide.reset", text="Back to Start", icon='LOOP_BACK')
        reset_row.prop(props, "start_frame", text="Frame")

        box.operator("blender_slide.play_anim",
                     text="Play / Pause Animation", icon='PLAY')

        box2 = layout.box()
        box2.label(text="Settings", icon='PREFERENCES')
        box2.prop(props, "switch_method", expand=True)

        box2.operator(
            "blender_slide.make_workspace",
            text="Presentation Workspace",
            icon='WINDOW',
        )

        box2.operator(
            "blender_slide.clean",
            text="Remove Invalid Slides",
            icon='TRASH',
        )

        box2.label(
            text="Enable shortcuts in Preferences > Add-ons",
            icon='INFO',
        )


# ============================================================
# Shortcuts (disabled by default; enable in add-on preferences)
# ============================================================
addon_keymaps = []


def _unregister_keymaps():
    for km, kmi in addon_keymaps:
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            pass

    addon_keymaps.clear()


def _register_keymaps():
    # Prevent duplicate registration
    _unregister_keymaps()

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon

    if not kc:
        return

    km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')

    for op_id, key in (
        ("blender_slide.next", 'PAGE_DOWN'),
        ("blender_slide.prev", 'PAGE_UP'),
    ):
        kmi = km.keymap_items.new(op_id, key, 'PRESS')
        addon_keymaps.append((km, kmi))


def _update_shortcuts(self, context):
    _unregister_keymaps()

    if self.use_shortcuts:
        _register_keymaps()


class BS_Preferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    use_shortcuts: bpy.props.BoolProperty(
        name="Register shortcuts (PageUp / PageDown)",
        description=(
            "Enable PageUp = Previous / PageDown = Next in the 3D Viewport. "
            "Leave this off if you are worried about conflicts with other "
            "add-ons or custom key configurations"
        ),
        default=False,
        update=_update_shortcuts,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "use_shortcuts")
        layout.label(
            text=("To change the keys, search for blender_slide.next / prev "
                  "in Preferences > Keymap"),
            icon='INFO',
        )


# ============================================================
# Registration
# ============================================================
classes = (
    BS_SlideItem,
    BS_Props,
    BS_UL_slides,
    BS_OT_add,
    BS_OT_remove,
    BS_OT_move,
    BS_OT_next,
    BS_OT_prev,
    BS_OT_reset,
    BS_OT_refresh,
    BS_OT_clean,
    BS_OT_play_anim,
    BS_OT_make_workspace,
    BS_PT_panel,
    BS_Preferences,
)


def register():
    for c in classes:
        bpy.utils.register_class(c)

    bpy.types.Scene.blender_slide = bpy.props.PointerProperty(type=BS_Props)

    try:
        prefs = bpy.context.preferences.addons[__name__].preferences
        if prefs and prefs.use_shortcuts:
            _register_keymaps()
    except (KeyError, AttributeError):
        pass


def unregister():
    _unregister_keymaps()

    del bpy.types.Scene.blender_slide

    for c in reversed(classes):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()

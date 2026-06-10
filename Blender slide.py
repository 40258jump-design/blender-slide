bl_info = {
    "name": "Blender Slide",
    "author": "Naga",
    "version": (1, 5, 1),
    "blender": (4, 2, 0),
    "location": "View3D > サイドバー(N) > Blender Slide",
    "description": "登録したコレクションをスライドとして表示切替するアドオン",
    "doc_url": "",
    "tracker_url": "",
    "category": "3D View",
}

import bpy


# ============================================================
# コア関数：現在のスライドだけ表示し、他は隠す
# ============================================================
def _find_layer_collection(view_layer, target_coll):
    """指定の Collection に対応する LayerCollection を再帰的に探す（同一性で照合）"""
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
    """コレクションをスライド管理から外す際、通常の表示状態へ戻す"""
    if coll is None:
        return

    lc = _find_layer_collection(context.view_layer, coll)
    if lc:
        lc.exclude = False
        lc.hide_viewport = False


def apply_slide_visibility(context):
    """切替方法に従って、現在のスライドだけ表示する"""
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
# プロパティ
# ============================================================
def _on_index_update(self, context):
    apply_slide_visibility(context)


def _on_method_update(self, context):
    apply_slide_visibility(context)


class BS_SlideItem(bpy.types.PropertyGroup):
    collection: bpy.props.PointerProperty(
        name="コレクション",
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
        name="切替方法",
        items=[
            ('EXCLUDE', "除外", "ビューレイヤーから除外（軽い・レンダリングにも反映）"),
            ('HIDE', "非表示", "ビューポートのみ非表示（レンダリングには影響しない）"),
        ],
        default='EXCLUDE',
        update=_on_method_update,
    )

    start_frame: bpy.props.IntProperty(
        name="開始フレーム",
        description="「最初に戻る」を押したときに移動するフレーム",
        default=1,
    )


# ============================================================
# UIList：スライド一覧
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
                text="%d. (未設定)" % (index + 1),
                icon='ERROR',
            )


# ============================================================
# オペレーター
# ============================================================
class BS_OT_add(bpy.types.Operator):
    bl_idname = "blender_slide.add"
    bl_label = "追加"
    bl_description = "アクティブなコレクションをスライドに追加"

    def execute(self, context):
        props = context.scene.blender_slide
        active_coll = context.view_layer.active_layer_collection.collection

        if active_coll is None or active_coll == context.scene.collection:
            self.report({'WARNING'}, "追加したいコレクションをアクティブにしてください")
            return {'CANCELLED'}

        if any(s.collection == active_coll for s in props.slides):
            self.report({'INFO'}, "「%s」は既に登録済みです" % active_coll.name)
            return {'CANCELLED'}

        item = props.slides.add()
        item.collection = active_coll
        props.active_index = len(props.slides) - 1

        self.report({'INFO'}, "「%s」を追加しました" % active_coll.name)
        return {'FINISHED'}


class BS_OT_remove(bpy.types.Operator):
    bl_idname = "blender_slide.remove"
    bl_label = "削除"
    bl_description = "選択中のスライドを一覧から削除"

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
    bl_label = "並べ替え"
    bl_description = "スライドの順番を上下に移動"

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
    bl_label = "次へ"
    bl_description = "次のスライドへ"

    def execute(self, context):
        props = context.scene.blender_slide

        if not props.slides:
            return {'CANCELLED'}

        props.active_index = (props.active_index + 1) % len(props.slides)
        return {'FINISHED'}


class BS_OT_prev(bpy.types.Operator):
    bl_idname = "blender_slide.prev"
    bl_label = "前へ"
    bl_description = "前のスライドへ"

    def execute(self, context):
        props = context.scene.blender_slide

        if not props.slides:
            return {'CANCELLED'}

        props.active_index = (props.active_index - 1) % len(props.slides)
        return {'FINISHED'}


class BS_OT_reset(bpy.types.Operator):
    bl_idname = "blender_slide.reset"
    bl_label = "最初に戻る"
    bl_description = "最初のスライドへ戻り、設定フレームへ移動する"

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
    bl_label = "表示を再適用"
    bl_description = "現在のスライドの表示状態を再適用する（Outliner手動操作後の復旧用）"

    def execute(self, context):
        apply_slide_visibility(context)
        return {'FINISHED'}


class BS_OT_clean(bpy.types.Operator):
    bl_idname = "blender_slide.clean"
    bl_label = "無効スライドを削除"
    bl_description = "コレクションが削除済み（未設定）のスライドを一覧から除去する"

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
            self.report({'INFO'}, "%d 件の無効スライドを削除しました" % removed)
        else:
            self.report({'INFO'}, "削除対象はありませんでした")

        apply_slide_visibility(context)
        return {'FINISHED'}


class BS_OT_play_anim(bpy.types.Operator):
    bl_idname = "blender_slide.play_anim"
    bl_label = "アニメ再生 / 停止"
    bl_description = "タイムラインの再生・停止を切り替える"

    def execute(self, context):
        bpy.ops.screen.animation_play()
        return {'FINISHED'}


class BS_OT_make_workspace(bpy.types.Operator):
    bl_idname = "blender_slide.make_workspace"
    bl_label = "プレゼン用WS生成"
    bl_description = "発表用ワークスペースを作成（カメラビュー＋UI非表示）"

    WS_NAME = "Presentation"

    def execute(self, context):
        existing = bpy.data.workspaces.get(self.WS_NAME)

        if existing:
            context.window.workspace = existing
            self.report({'INFO'}, "既存の Presentation に切り替えました")
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
            self.report({'WARNING'}, "3Dビューが見つかりませんでした")
        else:
            self.report({'INFO'}, "発表用ワークスペース『Presentation』を作成しました")

        return {'FINISHED'}


# ============================================================
# パネル（Nサイドバー）
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

        layout.label(text="スライド一覧", icon='SEQUENCE')

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
        header.label(text="現在： %d / %d" % (cur, n))
        header.operator("blender_slide.refresh", text="", icon='FILE_REFRESH')

        nav = box.row(align=True)
        nav.operator("blender_slide.prev", text="前へ", icon='TRIA_LEFT')
        nav.operator("blender_slide.next", text="次へ", icon='TRIA_RIGHT')

        reset_row = box.row(align=True)
        reset_row.operator("blender_slide.reset", text="最初に戻る", icon='LOOP_BACK')
        reset_row.prop(props, "start_frame", text="フレーム")

        box.operator("blender_slide.play_anim", text="アニメ再生 / 停止", icon='PLAY')

        box2 = layout.box()
        box2.label(text="設定", icon='PREFERENCES')
        box2.prop(props, "switch_method", expand=True)

        box2.operator(
            "blender_slide.make_workspace",
            text="プレゼン用WS生成",
            icon='WINDOW',
        )

        box2.operator(
            "blender_slide.clean",
            text="無効スライドを削除",
            icon='TRASH',
        )

        box2.label(
            text="ショートカットは Preferences > Add-ons で有効化",
            icon='INFO',
        )


# ============================================================
# ショートカット（既定OFF・アドオン設定で有効化）
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
    # 多重登録防止
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
        name="ショートカットを登録する（PageUp / PageDown）",
        description=(
            "3Dビューで PageUp=前へ / PageDown=次へ を有効にします。"
            "他アドオンや独自設定との競合が気になる場合はOFFのままにしてください"
        ),
        default=False,
        update=_update_shortcuts,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "use_shortcuts")
        layout.label(
            text="キーの変更は Preferences > Keymap で blender_slide.next / prev を検索",
            icon='INFO',
        )


# ============================================================
# 登録
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
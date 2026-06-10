# Blender Slide

![Blender Slide Panel](images/panel.png)

Blender Slide turns your Blender Collections into a simple slide presentation, so you can walk clients, classmates, or viewers through your 3D work without leaving Blender.

## Features

- Manage Blender Collections as slides
- Switch slides with Previous / Next buttons
- Exclude mode: lightweight and affects rendering
- Hide mode: viewport-only and does not affect rendering
- Create a clean presentation-friendly workspace
- Optional PageUp / PageDown shortcuts

## Installation

Requires Blender 4.2 or later.

1. Download [`blender_slide.py`](../../releases/latest) from the latest release.
2. Open Blender.
3. Go to `Edit > Preferences > Add-ons`.
4. Click `Install from Disk`.
5. Select `blender_slide.py`.
6. Enable `Blender Slide`.

## Where to Find the Panel

The Blender Slide panel is located in the 3D Viewport sidebar.

Press `N` in the 3D Viewport, then open the `Blender Slide` tab.

## Usage

1. Create Collections for each slide.
2. Make the Collection you want to add active.
3. Click the `+` button in the Blender Slide panel to add it as a slide.
4. Use `Prev` / `Next` to switch slides.
5. Use `Presentation Workspace` to create a clean workspace optimized for presenting your slides.

## Presentation Workspace

The `Presentation Workspace` button creates a clean Blender workspace for presenting.

It switches the 3D Viewport to camera view and hides overlays, gizmos, the toolbar, the sidebar, and the header.

## Switch Methods

### Exclude

Excludes non-current slide collections from the View Layer.

This is lightweight and also affects rendering.

### Hide

Hides non-current slide collections in the viewport only.

This does not affect rendering.

## Shortcuts

Shortcuts are disabled by default.

To enable them:

1. Open `Edit > Preferences > Add-ons`.
2. Find `Blender Slide`.
3. Enable `Register shortcuts (PageUp / PageDown)`.

Default shortcuts:

- `PageUp`: Previous slide
- `PageDown`: Next slide

You can change them in `Preferences > Keymap` by searching for:

- `blender_slide.prev`
- `blender_slide.next`

## Notes

- Collection names are used as slide labels.
- Slides are ordered by the order they were added.
- Some generic UI labels may be translated automatically depending on Blender's language setting.

## License

This project is licensed under the GNU General Public License v3.0.

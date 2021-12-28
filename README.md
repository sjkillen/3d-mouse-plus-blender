# 3DMousePlus Blender Addon
A Blender Addon for transforming objects with a 3DConnexion mouse
- Linux only
## Installation
- libspnav (https://github.com/FreeSpacenav/libspnav)
- Standard blender addon install (https://docs.blender.org/manual/en/latest/editors/preferences/addons.html#installing-add-ons)

## Use
- Transform mode is activated by pushing either button on the 3D mouse
- Uses the right button to toggle between "rotation only" and "translation only"
- Left button will renable both translation and rotation
- Space bar will toggle "bend mode"
- ESC, Enter, and left/right mouse buttons will exit transform mode
- Some properties can be adjusted in the popup menu immediately after exiting. Changing these settings will revert the transform
- Transforms will respect object and pose bone location/rotation locks
- Tested only in object and pose mode.

![A demo](./demo.gif)
# 3DMousePlus Blender Addon
A Blender Addon for transforming objects with a 3DConnexion mouse
- Linux only
## Installation
- libspnav (https://github.com/FreeSpacenav/libspnav)
- Standard blender addon install (https://docs.blender.org/manual/en/latest/editors/preferences/addons.html#installing-add-ons)

![A demo](./demo.gif)

## Use
- Transform mode is activated by pushing either button on the 3D mouse
- Transforms occur in global space transformed by the view matrix (Moving your viewport will affect how objects are transformed)
- Uses the right button to toggle between "rotation only" and "translation only"
- Left button will renable both translation and rotation
- Space bar will toggle "bend mode"
- ESC, Enter, and left/right mouse buttons will exit transform mode
- Tested only in object and pose mode.

## Configuration
- Properties can only be adjusted after exiting the operator (See Use) Changing these settings may revert the transform.
- Sensisitivy can be adjusted
- Transforms will respect object and pose bone location/rotation locks. Use those to limit the affected axises

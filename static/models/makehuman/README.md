Avatar Model Slot
=================

This folder is used by the Speech-to-Sign avatar panel to load a rigged
character model.

Expected file
-------------

- `avatar.glb`

Current default in this project:

- `avatar.glb` is sourced from:
  `mahakPandeyOfficial/3D-Avatar-React-Threejs`
  (model file `663e84d22bf045a79933e198.glb`)

If `avatar.glb` cannot be loaded, the app automatically falls back to the
procedural 3D avatar.

Recommended workflow
--------------------

1. Build or customize a character with your preferred pipeline.
2. Export the rigged character as `glTF` (`.glb`).
3. Save the file here as:
   `static/models/makehuman/avatar.glb`
4. Reload `/speech-to-sign` and open the `Avatar` tab.

Notes
-----

- `data-avatar-engine="auto"` on the avatar container means:
  try MakeHuman first, then fallback.
- Set `data-avatar-engine="procedural"` to force the old avatar.
- Bone names vary by exporter; arm/head motion is mapped best when common
  humanoid names are preserved in the skeleton.

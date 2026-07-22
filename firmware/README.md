# firmware/

This directory intentionally does not contain any Valve firmware binaries.

Valve Index Controller firmware (`.fw` files) is the property of Valve
Corporation and is not redistributed by this project. See the top-level
`README.md` "Legal notice" section.

To obtain the exact firmware files referenced throughout this
documentation, see `docs/04_firmware_acquisition.md`. Verify what you
obtain against `hashes/firmware_hashes.txt`.

If you build a patched firmware image using the scripts in `scripts/` or
`patches/`, verify your output against the corresponding hash in
`hashes/firmware_hashes.txt` before flashing it — this confirms your build
environment reproduced the exact same patch this documentation describes.

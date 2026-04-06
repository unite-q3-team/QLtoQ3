"""id md3 texture names."""

import os
import struct


def md3_tex(filepath):
    textures, issues = [], []
    try:
        filesize = os.path.getsize(filepath)
        if filesize < 108:
            return [], []
        with open(filepath, "rb") as f:
            data = f.read()
            if data[0:4] != b"IDP3":
                return [], []

            # md3 header:
            # 84: num_surfaces (int)
            # 100: ofs_surfaces (int)
            num_surfaces = struct.unpack("<I", data[84:88])[0]
            surf_offset = struct.unpack("<I", data[100:104])[0]

            if num_surfaces > 256 or surf_offset > filesize:
                return [], [
                    f"MD3 {os.path.basename(filepath)} has invalid header (surfs: {num_surfaces})"
                ]

            curr_surf = surf_offset
            for _ in range(num_surfaces):
                if curr_surf + 108 > filesize:
                    break

                # md3 surface offsets:
                # 76: num_shaders (int)
                # 92: ofs_shaders (int)
                # 104: ofs_end (int, offset to next surface)
                n_shaders = struct.unpack("<I", data[curr_surf + 76 : curr_surf + 80])[
                    0
                ]
                sh_off = struct.unpack("<I", data[curr_surf + 92 : curr_surf + 96])[0]
                next_off = struct.unpack("<I", data[curr_surf + 104 : curr_surf + 108])[
                    0
                ]

                if n_shaders > 256:
                    issues.append(
                        f"MD3 {os.path.basename(filepath)} has too many shaders ({n_shaders})"
                    )
                    break

                base_ptr = curr_surf + sh_off
                for s in range(n_shaders):
                    ptr = base_ptr + s * 68
                    if ptr + 64 > filesize:
                        break
                    name = (
                        data[ptr : ptr + 64]
                        .split(b"\x00")[0]
                        .decode("ascii", errors="ignore")
                    )
                    if name:
                        textures.append(name.lower().replace("\\", "/"))

                if next_off <= 0:
                    break
                curr_surf += next_off
    except Exception as e:
        issues.append(
            f"Failed to extract MD3 textures from {os.path.basename(filepath)}: {str(e)}"
        )
    return textures, issues

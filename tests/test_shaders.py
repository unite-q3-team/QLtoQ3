from qltoq3.constants import BRANDING_COMMENT
from qltoq3.shaders import process_shader, shader_deps


def test_shader_deps_extracts_paths_and_normalizes_slashes() -> None:
    shader_text = """
textures/example/surface
{
    map textures\\BASE/FLOOR.DDS
    clampmap "textures/Effects/Glow.PNG"
    qer_editorimage textures\\editor\\Preview
    q3map_lightimage "textures/LIGHTS/Lamp"
    sound sound/world/ambient.ogg
    map $lightmap
    animMap 8 textures/anim/frame1 textures\\ANIM\\FRAME2 "$whiteimage"
}
"""

    deps = shader_deps(shader_text)

    assert "textures/base/floor.dds" in deps
    assert "textures/effects/glow.png" in deps
    assert "textures/editor/preview" in deps
    assert "textures/lights/lamp" in deps
    assert "sound/world/ambient.ogg" in deps
    assert "textures/anim/frame1" in deps
    assert "textures/anim/frame2" in deps
    assert "$lightmap" not in deps
    assert "$whiteimage" not in deps


def test_process_shader_adds_branding_and_rewrites_extensions(tmp_path) -> None:
    shader_file = tmp_path / "example.shader"
    shader_file.write_text(
        """
textures/test
{
    map textures/foo/brick.dds
    clampmap "textures/foo/glow.PNG"
}
""".lstrip("\n"),
        encoding="utf-8",
    )

    ok, error, transformed = process_shader(str(shader_file))

    assert ok is True
    assert error is None
    assert transformed is not None
    assert transformed.startswith(BRANDING_COMMENT)
    assert ".dds" not in transformed.lower()
    assert ".png" not in transformed.lower()
    assert "textures/foo/brick.tga" in transformed
    assert "textures/foo/glow.tga" in transformed

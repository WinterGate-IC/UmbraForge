"""Document model: geometry, ordering, assets, serialization and undo."""

from __future__ import annotations

import struct

import pytest

from umbraforge.layers import (
    FORMAT_VERSION,
    MAX_LAYERS,
    Design,
    History,
    IconLayer,
    ImageLayer,
    Layer,
    ShapeLayer,
    TextLayer,
    add_asset,
    asset_bytes,
    asset_image_size,
    asset_name,
    default_adjustments,
    default_effects,
    merge,
)


# --------------------------------------------------------------------------
# layers
# --------------------------------------------------------------------------
def test_center_and_rect_helpers():
    layer = ShapeLayer(x=0.1, y=0.2, w=0.4, h=0.2)
    assert layer.center() == pytest.approx((0.3, 0.3))
    layer.set_center(0.5, 0.5)
    assert (layer.x, layer.y) == pytest.approx((0.3, 0.4))
    assert layer.normalized_rect() == pytest.approx((0.3, 0.4, 0.4, 0.2))


def test_clamp_to_canvas_sanitizes_values():
    layer = ShapeLayer(
        x=99.0, y=-99.0, w=50.0, h=0.0001, rotation=720.0, opacity=4.0,
        blend="not-a-mode")
    layer.clamp_to_canvas()
    assert layer.w == 4.0
    assert layer.h == 0.001
    assert layer.rotation == 360.0
    assert layer.opacity == 1.0
    assert layer.blend == "normal"
    assert layer.x <= 0.9
    assert layer.y >= -2.0
    assert layer.effects["shadow"]["enabled"] is False


def test_merge_keeps_defaults_and_ignores_unknown_keys():
    merged = merge(default_effects(), {"glow": {"enabled": True},
                                       "nonsense": 42})
    assert merged["glow"]["enabled"] is True
    assert merged["glow"]["color"] == default_effects()["glow"]["color"]
    assert merged["shadow"]["enabled"] is False
    assert "nonsense" not in merged


@pytest.mark.parametrize("layer", [
    ShapeLayer(name="Crest", shape="shield", fill="#ff0000", fill2="#0000ff",
               gradient=True, gradient_angle=45.0, stroke="#ffffff",
               stroke_width=0.02, x=0.2, y=0.1, w=0.5, h=0.6,
               rotation=12.5, opacity=0.8, blend="screen"),
    IconLayer(name="Bolt", icon="bolt", color="#ffcc00", gradient=True,
              fill2="#ff7a3d", x=0.4, y=0.4, w=0.2, h=0.2),
    TextLayer(name="Title", text="UMBRA\nFORGE", font="Georgia", size=0.08,
              weight=800, italic=True, letter_spacing=0.12, line_height=1.3,
              uppercase=True, align="left", valign="top", color="#eeeeee",
              stroke_color="#000000", stroke_width=0.01),
    ImageLayer(name="Photo", asset_id="abc123", original_asset_id="orig",
               fit="cover", mask="circle", mask_feather=0.03,
               adjustments={**default_adjustments(), "brightness": 1.2,
                            "saturation": 0.8}),
], ids=["shape", "icon", "text", "image"])
def test_layer_roundtrip(layer):
    layer.clamp_to_canvas(keep_visible=False)
    payload = layer.to_dict()
    restored = Layer.from_dict(payload)
    assert type(restored) is type(layer)
    assert restored.to_dict() == payload


def test_unknown_layer_kind_falls_back_to_shape():
    restored = Layer.from_dict({"kind": "from-the-future", "name": "Odd",
                                "w": 0.4, "h": 0.4})
    assert isinstance(restored, ShapeLayer)
    assert restored.name == "Odd"


def test_clone_gets_a_new_id_and_offset():
    layer = ShapeLayer(name="Base", x=0.2, y=0.2, w=0.3, h=0.3)
    clone = layer.clone()
    assert clone.id != layer.id
    assert clone.name == "Base copy"
    assert (clone.x, clone.y) == pytest.approx((0.22, 0.22))
    clone.fill = "#00ff00"
    assert layer.fill != clone.fill


# --------------------------------------------------------------------------
# design operations
# --------------------------------------------------------------------------
def test_add_select_remove_and_duplicate():
    design = Design()
    first = design.add(ShapeLayer(name="First"))
    second = design.add(ShapeLayer(name="Second"))
    assert design.selected == second.id
    assert design.active is second
    assert design.layer(first.id) is first
    assert design.layer("missing") is None
    assert design.layer_count() == 2

    copy = design.duplicate(first.id)
    assert copy is not None
    assert design.layers.index(copy) == design.layers.index(first) + 1
    assert copy.name == "First copy"
    assert design.selected == copy.id

    design.remove(second.id)
    assert design.layer(second.id) is None
    assert design.selected == copy.id

    design.remove(copy.id)
    design.remove(first.id)
    assert design.layers == []
    assert design.selected is None


def test_move_and_order_helpers():
    design = Design()
    a = design.add(ShapeLayer(name="A"))
    b = design.add(ShapeLayer(name="B"))
    c = design.add(ShapeLayer(name="C"))
    assert design.top_first() == [c, b, a]

    assert design.move(a.id, 1) is True
    assert design.layers == [b, a, c]
    assert design.move(b.id, -1) is False

    assert design.to_front(b.id) is True
    assert design.layers == [a, c, b]
    assert design.to_front(b.id) is False

    assert design.to_back(b.id) is True
    assert design.layers == [b, a, c]
    assert design.to_back(b.id) is False

    design.center_layer(a.id)
    assert a.center() == pytest.approx((0.5, 0.5))


def test_insert_clamps_index_and_unique_names():
    design = Design()
    design.add(ShapeLayer(name="Shape"))
    design.insert(99, ShapeLayer(name="Last"))
    assert design.layers[-1].name == "Last"
    design.insert(-5, ShapeLayer(name="First"))
    assert design.layers[0].name == "First"

    assert design.unique_name("New") == "New"
    assert design.unique_name("Shape") == "Shape 2"
    design.add(ShapeLayer(name="Shape 2"))
    assert design.unique_name("Shape") == "Shape 3"


def test_layer_limit_is_enforced():
    design = Design()
    for index in range(MAX_LAYERS):
        design.add(ShapeLayer(name=f"Layer {index}"))
    with pytest.raises(ValueError):
        design.add(ShapeLayer(name="Too many"))
    with pytest.raises(ValueError):
        design.insert(0, ShapeLayer(name="Too many"))


# --------------------------------------------------------------------------
# assets
# --------------------------------------------------------------------------
def test_assets_are_content_addressed_and_decodable():
    assets: dict = {}
    data = b"\x89PNG\r\n\x1a\nfake-body"
    first = add_asset(assets, data, "one.png", "image/png", 10, 20)
    second = add_asset(assets, data, "two.png", "image/png", 10, 20)
    assert first == second
    assert len(assets) == 1
    assert asset_bytes(assets, first) == data
    assert asset_name(assets, first) == "two.png"
    assert asset_bytes(assets, "nope") is None
    assert asset_name(assets, "nope") == "missing image"


def test_asset_image_size_reads_png_header():
    header = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
              + struct.pack(">II", 321, 123) + b"\x00" * 8)
    assert asset_image_size(header) == (321, 123)
    assert asset_image_size(b"not an image") == (0, 0)


# --------------------------------------------------------------------------
# serialization
# --------------------------------------------------------------------------
def build_document() -> Design:
    design = Design(name="Crest")
    design.set_size(900, 1600)
    design.background.update(kind="solid", color="#112233", pattern="dots")
    design.add(ShapeLayer(name="Shield", shape="shield", fill="#ff7a3d"))
    design.add(TextLayer(name="Word", text="WINTERGATE"))
    design.add(IconLayer(name="Star", icon="star"))
    design.assets["asset"] = {"name": "pic.png", "mime": "image/png",
                              "data": "ZmFrZQ==", "w": 4, "h": 5}
    design.add(ImageLayer(name="Pic", asset_id="asset"))
    return design


def test_document_roundtrip():
    design = build_document()
    data = design.to_dict()
    restored = Design.from_dict(data)
    assert restored.to_dict() == data
    assert restored.name == "Crest"
    assert (restored.width, restored.height) == (900, 1600)
    assert restored.background["pattern"] == "dots"
    assert [type(layer) for layer in restored.layers] == [
        ShapeLayer, TextLayer, IconLayer, ImageLayer]
    assert restored.selected == design.layers[-1].id
    assert asset_bytes(restored.assets, "asset") == b"fake"


def test_save_and_open(tmp_path):
    design = build_document()
    path = design.save(tmp_path / "crest")
    assert path.name == "crest.umbra"
    assert path.exists()
    loaded = Design.open(path)
    assert loaded.name == "Crest"
    assert len(loaded.layers) == 4
    assert loaded.to_dict() == design.to_dict()

    # A UTF-8 BOM should not upset the reader.
    path.write_text("\ufeff" + path.read_text(encoding="utf-8"),
                    encoding="utf-8")
    assert Design.open(path).name == "Crest"


def test_open_rejects_foreign_and_future_files(tmp_path):
    bad = tmp_path / "bad.umbra"
    bad.write_text('{"format": "something-else"}', encoding="utf-8")
    with pytest.raises(ValueError, match="not an UmbraForge"):
        Design.open(bad)

    future = tmp_path / "future.umbra"
    future.write_text(
        '{"format": "umbraforge", "version": %d}' % (FORMAT_VERSION + 1),
        encoding="utf-8")
    with pytest.raises(ValueError, match="newer"):
        Design.open(future)

    broken = tmp_path / "broken.umbra"
    broken.write_text("{not json", encoding="utf-8")
    with pytest.raises(Exception):
        Design.open(broken)


def test_load_dict_skips_junk_and_limits_layers():
    raw = {
        "format": "umbraforge",
        "name": "Junk",
        "width": 500,
        "height": 500,
        "layers": ["not a layer", {"kind": "shape", "w": "wide"},
                   {"kind": "text", "w": 0.4, "h": 0.2}],
        "selected": "not-a-real-id",
    }
    design = Design.from_dict(raw)
    assert [type(layer) for layer in design.layers] == [ShapeLayer, TextLayer]
    assert design.layers[0].w == 0.5  # bad float fell back to the default
    assert design.selected == design.layers[-1].id

    many = {"layers": [{"kind": "shape"} for _ in range(MAX_LAYERS + 10)]}
    assert len(Design.from_dict(many).layers) == MAX_LAYERS


def test_clone_is_independent():
    design = build_document()
    clone = design.clone()
    clone.layers[0].fill = "#00ff00"
    clone.background["color"] = "#ffffff"
    assert design.layers[0].fill != "#00ff00"
    assert design.background["color"] != "#ffffff"
    assert clone.layers[0].id == design.layers[0].id


# --------------------------------------------------------------------------
# undo
# --------------------------------------------------------------------------
def test_undo_and_redo_travel_the_snapshots():
    design = Design()
    history = History(design)
    assert not history.can_undo
    assert not history.can_redo
    assert not history.push("No change", "same", coalesce_seconds=0)

    design.name = "One"
    assert history.push("Rename", "name", coalesce_seconds=0) is True
    design.name = "Two"
    assert history.push("Rename", "name", coalesce_seconds=0) is True
    assert history.labels() == ["Opened", "Rename", "Rename"]
    assert history.can_undo

    assert history.undo() is True
    assert design.name == "One"
    assert history.undo() is True
    assert design.name == "Untitled"
    assert history.undo() is False

    assert history.redo() is True
    assert design.name == "One"
    assert history.redo() is True
    assert design.name == "Two"
    assert history.redo() is False


def test_undo_coalesces_slider_style_pushes():
    design = Design()
    history = History(design)
    design.name = "A"
    assert history.push("Opacity", "opacity-1", coalesce_seconds=60) is True
    design.name = "B"
    assert history.push("Opacity", "opacity-1", coalesce_seconds=60) is False
    assert history.labels() == ["Opened", "Opacity"]

    history.undo()
    assert design.name == "Untitled"
    history.redo()
    assert design.name == "B"


def test_new_push_after_undo_drops_the_redo_branch():
    design = Design()
    history = History(design)
    design.name = "One"
    history.push("One", "one", coalesce_seconds=0)
    design.name = "Two"
    history.push("Two", "two", coalesce_seconds=0)
    history.undo()
    assert history.can_redo

    design.name = "Three"
    history.push("Three", "three", coalesce_seconds=0)
    assert not history.can_redo
    history.undo()
    assert design.name == "One"


def test_history_limit_keeps_recent_steps():
    design = Design()
    history = History(design, limit=3)
    for index in range(6):
        design.name = f"Step {index}"
        history.push(f"Step {index}", f"key-{index}", coalesce_seconds=0)
    assert len(history.labels()) == 3
    assert history.labels()[-1] == "Step 5"
    assert history.cursor == 2

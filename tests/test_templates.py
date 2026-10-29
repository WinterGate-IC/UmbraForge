"""The starter gallery."""

from __future__ import annotations

import pytest

from umbraforge import renderer, templates
from umbraforge.layers import Design, ImageLayer, ShapeLayer, TextLayer


def test_template_keys_and_categories_are_sane():
    keys = [template.key for template in templates.TEMPLATES]
    assert len(keys) == len(set(keys))
    assert len(keys) >= 10
    for template in templates.TEMPLATES:
        assert template.name and template.note and template.category
        assert callable(template.build)
    categories = templates.categories()
    assert len(categories) == len(set(categories))
    assert "Featured" in categories


def test_get_lookup():
    first = templates.TEMPLATES[0]
    assert templates.get(first.key) is first
    assert templates.build(first.key).name == first.name
    with pytest.raises(KeyError):
        templates.get("nope")
    with pytest.raises(KeyError):
        templates.build("nope")


@pytest.mark.parametrize("template", templates.TEMPLATES, ids=lambda t: t.key)
def test_each_template_is_a_complete_design(template):
    design = templates.build(template.key)
    assert design.name == template.name
    assert design.width >= 64 and design.height >= 64
    assert design.preset_key != "custom"
    assert design.layers, "a template with no layers is not a starting point"

    ids = [layer.id for layer in design.layers]
    assert len(ids) == len(set(ids))
    for layer in design.layers:
        assert layer.visible
        assert 0.001 <= layer.w <= 4.0
        assert 0.001 <= layer.h <= 4.0
        assert -2.0 <= layer.x <= 2.0
        assert -2.0 <= layer.y <= 2.0
        assert 0.0 <= layer.opacity <= 1.0
        assert not isinstance(layer, ImageLayer)

    kinds = {type(layer) for layer in design.layers}
    assert ShapeLayer in kinds or len(design.layers) > 0


@pytest.mark.parametrize("template", templates.TEMPLATES, ids=lambda t: t.key)
def test_templates_roundtrip_and_render(template, qapp):
    design = templates.build(template.key)
    clone = Design.from_dict(design.to_dict())
    assert clone.to_dict() == design.to_dict()
    image = renderer.render_thumbnail(design, 120)
    assert not image.isNull()
    assert max(image.width(), image.height()) <= 120


def test_templates_include_text_and_vector_work():
    texts = 0
    vectors = 0
    for template in templates.TEMPLATES:
        design = template.build()
        texts += sum(isinstance(layer, TextLayer) for layer in design.layers)
        vectors += sum(isinstance(layer, ShapeLayer) for layer in design.layers)
    assert texts >= len(templates.TEMPLATES) // 2
    assert vectors >= len(templates.TEMPLATES)

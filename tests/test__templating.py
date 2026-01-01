import pytest

from workflows_acp._templating import Template, TemplateValidationError


def test_template() -> None:
    template_str = """
I ate {{food}} and I drank {{drink}}.
"""
    template = Template(template_str)
    assert (
        len(template._to_render) == 2
        and "food" in template._to_render
        and "drink" in template._to_render
    )
    assert template.content == template_str
    result = template.render({"food": "pizza", "drink": "water"})
    assert result == "\nI ate pizza and I drank water.\n"
    with pytest.raises(TemplateValidationError):
        template.render({"food": "pizza"})
    with pytest.raises(TemplateValidationError):
        template.render({"food": "pizza", "drink": 100})  # type: ignore

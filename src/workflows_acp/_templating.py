import re

PATTERN = re.compile(r"\{\{([^\}]+)\}\}")


class TemplateValidationError(Exception):
    """Raised when the arguments to render a template fail to validate"""


class Template:
    def __init__(self, content: str):
        self.content = content
        self._to_render = PATTERN.findall(content)

    def _validate(self, args: dict[str, str]) -> bool:
        return all(el in args for el in self._to_render) and all(
            isinstance(args[k], str) for k in args
        )

    def render(self, args: dict[str, str]) -> str:
        if self._validate(args):
            content = self.content
            for word in self._to_render:
                content = content.replace("{{" + word + "}}", args[word])
            return content
        else:
            if (ls := list(set(self._to_render) - set(list(args.keys())))) != []:
                raise TemplateValidationError(
                    f"Missing the following arguments for the template: {', '.join(ls)}"
                )
            else:
                raise TemplateValidationError(
                    "You should provide a dictionary with only string values."
                )

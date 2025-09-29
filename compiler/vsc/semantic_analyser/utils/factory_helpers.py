from vsc.parser.core.classes import *
from vsc.parser.utils.factory_helpers import get_boolean_literal, get_directive, get_import, get_span


def get_root_with_import(
    main_file_path: str,
    imports: List[str],
    is_module: bool = False,
):
    directives = [get_directive("module", value=get_boolean_literal(True))] if is_module else []
    return Root(
        file_path=main_file_path,
        imports=[get_import(path) for path in imports],
        directives=directives,
        execution_steps=[],
        function_definitions=[],
        span=get_span(),
    )

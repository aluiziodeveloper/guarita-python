from mcp.types import Tool

from guarita.fingerprint import canonical, fingerprint

SCHEMA = {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}


def read_file(description: str = "Lê um arquivo.", **extra: object) -> Tool:
    return Tool.model_validate(
        {"name": "read_file", "description": description, "inputSchema": SCHEMA, **extra}
    )


def test_is_a_sha256_in_hex() -> None:
    assert len(fingerprint(read_file())) == 64


def test_key_order_does_not_change_the_fingerprint() -> None:
    reordered = Tool.model_validate(
        {
            "inputSchema": {
                "required": ["path"],
                "properties": {"path": {"type": "string"}},
                "type": "object",
            },
            "description": "Lê um arquivo.",
            "name": "read_file",
        }
    )
    assert fingerprint(reordered) == fingerprint(read_file())


def test_one_character_in_the_description_changes_it() -> None:
    assert fingerprint(read_file("Lê um arquivo!")) != fingerprint(read_file())


def test_a_change_in_the_schema_changes_it() -> None:
    wider = Tool.model_validate(
        {"name": "read_file", "description": "Lê um arquivo.", "inputSchema": {"type": "object"}}
    )
    assert fingerprint(wider) != fingerprint(read_file())


def test_metadata_outside_the_definition_is_ignored() -> None:
    with_meta = read_file(_meta={"trace": "abc"})
    assert canonical(with_meta) == canonical(read_file())

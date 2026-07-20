import json

from app.core.aliases import load_aliases


def test_load_aliases_returns_empty_dict_when_path_is_none() -> None:
    assert load_aliases(None) == {}


def test_load_aliases_returns_empty_dict_when_file_missing(tmp_path) -> None:
    missing = tmp_path / "does_not_exist.json"

    assert load_aliases(str(missing)) == {}


def test_load_aliases_reads_alias_map_from_file(tmp_path) -> None:
    alias_file = tmp_path / "aliases.json"
    alias_file.write_text(json.dumps({"aliases": {"purchases": ["orders", "order_items"]}}))

    assert load_aliases(str(alias_file)) == {"purchases": ["orders", "order_items"]}

from transcription_bot.file_api.utils import apply_recursively


def test_apply_recursively():
    test_dict = {
        "value": "test {replace_me}",
        "value2": "test2 {replace_me}",
        "value3": 10,
    }

    def f(val: str):
        return val.format(replace_me="replaced")

    apply_recursively(f, test_dict, lambda v: isinstance(v, str))

    assert test_dict == {
        "value": "test replaced",
        "value2": "test2 replaced",
        "value3": 10,
    }


def test_apply_recursively_with_nested_items():
    test_dict = {"value": 1, "a_dict": {"value": "test {dont_replace_me}", "value2": 2}}

    def f(val: int):
        return val + 1

    apply_recursively(f, test_dict, lambda v: isinstance(v, int))

    assert test_dict == {
        "value": 2,
        "a_dict": {"value": "test {dont_replace_me}", "value2": 3},
    }


def test_apply_recursively_nested_list_of_dicts_and_nested_lists():
    test_dict = {
        "value1": 1,
        "value2": [1, {"value": 1, "another_value": "some string"}, [1, {"value": 1}]],
    }

    def f(val: int):
        return val + 1

    apply_recursively(f, test_dict, lambda v: isinstance(v, int))

    assert test_dict == {
        "value1": 2,
        "value2": [1, {"value": 2, "another_value": "some string"}, [1, {"value": 2}]],
    }

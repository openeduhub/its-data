from collections.abc import Callable, Sequence
from typing import Any, Optional

import data_utils.filters as filters
import hypothesis.strategies as st
from data_utils.utils import Nested_Dict
from hypothesis import given


def cut_subtree(base_dict: Nested_Dict, key: str) -> Nested_Dict:
    return Nested_Dict(
        {
            base_key: base_value
            for base_key, base_value in base_dict.items()
            if base_key != key
        }
    )


garbage = st.one_of(
    st.text(),
    st.integers(),
    st.floats(),
    st.none(),
)


@st.composite
def replace_subtree(draw: st.DrawFn, base_dict: Nested_Dict, key: str) -> Nested_Dict:
    # make sure that the new value does not equal the old one
    while (new_value := draw(garbage)) == base_dict[key]:
        pass
    return Nested_Dict(
        {
            base_key: base_value if base_key != key else new_value
            for base_key, base_value in base_dict.items()
        }
    )


@st.composite
def add_garbage(draw: st.DrawFn, base_dict: Nested_Dict) -> Nested_Dict:
    while (key := draw(st.text())) in base_dict:
        pass

    value = draw(garbage)
    return Nested_Dict(
        {base_key: base_value for base_key, base_value in base_dict.items()}
        | {key: value}
    )


@st.composite
def recursively_mutated_dict(
    draw: st.DrawFn,
    base_dict: Nested_Dict,
    key: str,
    index: int | None = None,
    **kwargs,
) -> Nested_Dict:
    followed_dict = base_dict[key]
    if index is None:
        assert isinstance(followed_dict, dict)
        return Nested_Dict(
            {
                base_key: base_value
                if base_key != key
                else draw(mutated_nested_dict(followed_dict, **kwargs))
                for base_key, base_value in base_dict.items()
            }
        )

    assert isinstance(followed_dict, list)
    followed_dict = followed_dict[index]
    assert isinstance(followed_dict, dict)
    return Nested_Dict(
        {
            base_key: base_value
            if base_key != key
            else draw(mutated_nested_dict(followed_dict, **kwargs))
            for base_key, base_value in base_dict.items()
        }
    )


@st.composite
def mutated_nested_dict(
    draw: st.DrawFn,
    base_dict: Nested_Dict,
    allow_cut=True,
    allow_replace=True,
    allow_add_key=True,
    allow_add_to_list=True,
    allow_remove_from_list=True,
    add_whitelist: Optional[Sequence[Any]] = None,
    add_blacklist: Optional[Sequence[Any]] = None,
    min_iters: int = 1,
    max_iters: int = 1,
) -> Nested_Dict:
    kwargs = {
        "allow_cut": allow_cut,
        "allow_replace": allow_replace,
        "allow_add_key": allow_add_key,
        "allow_add_to_list": allow_add_to_list,
        "allow_remove_from_list": allow_remove_from_list,
        "add_whitelist": add_whitelist,
        "add_blacklist": add_blacklist,
    }
    iters = draw(st.integers(min_iters, max_iters))
    for _ in range(iters):
        key = draw(st.sampled_from(list(base_dict.keys())))
        value = base_dict[key]
        actions: list[Callable[[], Nested_Dict]] = list()

        # remove this key and its value
        if allow_cut:
            actions.append(lambda: cut_subtree(base_dict, key))
        # keep the key but replace its value with a random terminal value
        if allow_replace:
            actions.append(lambda: draw(replace_subtree(base_dict, key)))
        # add a random new key with a random terminal value
        if allow_add_key:
            actions.append(lambda: draw(add_garbage(base_dict)))

        # recursively mutate the underlying nested dictionary
        if isinstance(value, dict):
            actions.append(
                lambda: draw(recursively_mutated_dict(base_dict, key, **kwargs))
            )

        elif isinstance(value, list):
            # add a random value to the list
            if allow_add_to_list:
                added_value = (
                    draw(garbage)
                    if add_whitelist is None
                    else draw(st.sampled_from(add_whitelist))
                )
                if add_blacklist is not None:
                    while added_value in add_blacklist:
                        added_value = (
                            draw(garbage)
                            if add_whitelist is None
                            else draw(st.sampled_from(add_whitelist))
                        )

                actions.append(
                    lambda: Nested_Dict(
                        {
                            base_key: base_value
                            if base_key != key
                            else value + [added_value]
                            for base_key, base_value in base_dict.items()
                        }
                    )
                )

            if len(value) > 0:
                index = draw(st.sampled_from(range(len(value))))

                # remove a random value from the list
                if allow_remove_from_list:
                    value_without_index = [x for i, x in enumerate(value) if i != index]
                    actions.append(
                        lambda: Nested_Dict(
                            {
                                base_key: base_value
                                if base_key != key
                                else value_without_index
                                for base_key, base_value in base_dict.items()
                            }
                        )
                    )

                # recursively mutate a random subtree from the list
                if isinstance(value[index], dict):
                    actions.append(
                        lambda: draw(
                            recursively_mutated_dict(base_dict, key, index, **kwargs)
                        )
                    )

        action = draw(st.sampled_from(actions))
        base_dict = action()

    return base_dict


@given(
    mutated_nested_dict(
        {
            "nodeRef": {"storeRef": {"protocol": "workspace"}},
            "type": "ccm:io",
            "properties": {"cm:edu_metadataset": "mds_oeh"},
            "aspects": [],
        },
        add_blacklist=["ccm:collection_io_reference"],
        allow_cut=False,
        allow_replace=False,
    )
)
def test_kibana_basic_filter_accepts_from_minimal(entry: Nested_Dict):
    assert filters.kibana_basic_filter(entry)


@given(
    mutated_nested_dict(
        {
            "nodeRef": {"storeRef": {"protocol": "workspace"}},
            "type": "ccm:io",
            "properties": {"cm:edu_metadataset": "mds_oeh"},
            "aspects": [],
        },
        add_whitelist=["ccm:collection_io_reference"],
        allow_remove_from_list=False,
        allow_add_key=False,
    )
)
def test_kibana_basic_filter_rejects_from_minimal(entry: Nested_Dict):
    assert not filters.kibana_basic_filter(entry)


@given(
    mutated_nested_dict(
        {
            "nodeRef": {"storeRef": {"protocol": "workspace"}},
            "type": "ccm:io",
            "properties": {"cm:edu_metadataset": "mds_oeh"},
            "aspects": ["ccm:collection_io_reference"],
        },
        allow_add_to_list=True,
        allow_remove_from_list=False,
    )
)
def test_kibana_basic_filter_rejects_with_bad_aspect(entry: Nested_Dict):
    assert not filters.kibana_basic_filter(entry)

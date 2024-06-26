"""
Module for downloading content from the internet.
"""
from __future__ import annotations

import gzip
import json
import shutil
import urllib.request
from collections import defaultdict
from collections.abc import Collection, Iterable, Iterator, Sequence
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from tqdm import tqdm

import its_data.transform as trans
from its_data.data import (
    Basic_Value,
    Basic_Value_Not_None,
    Data_Point,
    Terminal_Value,
    get_children_map,
    get_in,
    get_leaves,
    get_parent_map,
    get_terminal_in,
)
from its_data.filters import Filter


def fetch(
    base_url: str,
    target_file: str = "workspace_data-public-only.json.gz",
    output_dir: str | Path = Path("/tmp"),
    output_file: Optional[str | Path] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    encoded_auth: Optional[str] = None,
    skip_if_exists: bool = True,
    delete_compressed_archive: bool = True,
) -> Path:
    """
    Download the latest data dump and save it to the given directory.

    :param base_url: The base URL from which to download the data.
    :param target_file: The file from the base URL to download.

      - Assumption: the file is located at `base_url/target_file`
    :param output_dir: The directory in which to save the downloaded file.
    :param output_file: The name of the file to download.
      By default, this is equal to `target_file` (without `.gz`, if applicable).
    :param username: The (Basic Auth) username to use for authorization.
    :param password: The (Basic Auth) password to use for authorization.
    :param encoded_auth: The already encoded username+password combination.
      If set, `username` and `password` are ignored.
    :param skip_if_exists:

      - If set to True, skip download if the output file
        already exists.
      - If set to False, always override any already present files.
    :param delete_compressed_archive: Whether to delete the compressed archive
      after it has been decompressed.
    :returns: The path to the (decompressed) downloaded file.
    """
    # convert to pathlib.Path if the path was given as a string
    if isinstance(output_dir, str):
        output_dir = Path(output_dir)

    # expand the home user directory path, if it was given symbolically
    output_dir = output_dir.expanduser()

    download_file = output_dir / target_file

    if output_file is None:
        if ".gz" == download_file.__str__()[-3:]:
            output_file = download_file.with_suffix(download_file.suffix[:-3])
        else:
            output_file = download_file
    elif isinstance(output_file, str):
        output_file = output_dir / output_file

    if skip_if_exists and output_file.exists():
        print(f"File at {output_file} already exists.")
        print("Set skip_if_exists to False to force re-download.")
        return output_file

    if skip_if_exists and download_file.exists():
        print(f"File at {download_file} already exists.")
        print("Set skip_if_exists to False to force re-download.")

    else:
        # remove trailing / from url
        if "/" == base_url[-1]:
            base_url = base_url[:-1]

        url = "/".join([base_url, target_file])
        headers = None

        # handle authentication, if supplied
        if username is not None and password is not None:
            password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
            password_mgr.add_password(None, base_url, username, password)
            handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
            opener = urllib.request.build_opener(handler)
            urllib.request.install_opener(opener)

        elif encoded_auth is not None:
            headers = {"Authorization": f"Basic {encoded_auth}"}

        _download(url=url, target_path=download_file, headers=headers)

    # if the file was gzipped, decompress it
    # act on the file on disk to avoid loading the entire file to RAM
    if output_file != download_file:
        print("Decompressing data...")
        with gzip.open(download_file, "rb") as f_in:
            with open(output_file, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        if delete_compressed_archive:
            download_file.unlink()

    return output_file


def _download(url: str, target_path: Path, headers: Optional[dict[str, str]] = None):
    print("Downloading data...")
    with urllib.request.urlopen(
        urllib.request.Request(
            url,
            headers=headers,
        )
        if headers is not None
        else url
    ) as r:
        with open(target_path, "wb") as f:
            # use shutil.copyfileobj to avoid loading the entire file to RAM
            shutil.copyfileobj(r, f)


def _dict_from_json_entry(
    raw_entry: Data_Point,
    columns: Iterable[str] | dict[str, str],
    key_separator: str = ".",
) -> dict[str, Terminal_Value]:
    entry: dict[str, Terminal_Value] = dict()
    if isinstance(columns, dict):
        for key, column in columns.items():
            entry[key] = get_terminal_in(raw_entry, column.split(key_separator))
    else:
        for column in columns:
            entry[column] = get_terminal_in(raw_entry, column.split(key_separator))

    return entry


def num_entries(path: Path) -> int:
    hits = 0
    with open(path) as f:
        for _ in f:
            hits += 1

    return hits


def raw_entry_generator(
    path: Path, key_separator: str, prefix: Optional[str], max_len: Optional[int]
) -> Iterator[Data_Point]:
    hits = 0
    with open(path) as f:
        # because we are dealing with line-separated jsons,
        # read the file one line at a time
        for line in f:
            if max_len is not None and hits >= max_len:
                break

            # get only the sub-entry at the prefix, if a prefix was given
            if prefix is not None:
                raw_entry = get_in(json.loads(line), prefix.split(key_separator))
            else:
                raw_entry = json.loads(line)

            if not isinstance(raw_entry, dict):
                raise ValueError(
                    f"The given prefix key {prefix} does not exists for all entries or does not point to a map!"
                )

            hits += 1
            yield raw_entry


def _dicts_from_json_file(
    path: Path,
    columns: Iterable[str] | dict[str, str],
    key_separator: str,
    prefix: Optional[str],
    filters: Collection[Filter],
    dropped_values: dict[str, Collection[Basic_Value_Not_None]],
    remapped_values: dict[str, dict[Basic_Value_Not_None, Basic_Value]],
    max_len: Optional[int],
) -> Iterator[dict[str, Terminal_Value]]:
    modified_fields = set(dropped_values.keys()) | set(remapped_values.keys())
    for raw_entry in tqdm(
        raw_entry_generator(
            path, key_separator=key_separator, prefix=prefix, max_len=max_len
        ),
        total=num_entries(path),
    ):
        for field in modified_fields:
            raw_entry = trans.with_changed_value(
                raw_entry,
                field.split(key_separator),
                dropped_values[field],
                remapped_values[field],
            )

        if all(fun(raw_entry) for fun in filters):
            yield _dict_from_json_entry(
                raw_entry, columns=columns, key_separator=key_separator
            )


def df_from_json_file(
    path: Path,
    columns: Iterable[str] | dict[str, str],
    prefix: Optional[str] = "_source",
    key_separator: str = ".",
    filters: Collection[Filter] = tuple(),
    dropped_values: dict[str, Collection[Basic_Value_Not_None]] = dict(),
    remapped_values: dict[str, dict[Basic_Value_Not_None, Basic_Value]] = dict(),
    max_len: Optional[int] = None,
) -> pd.DataFrame:
    """
    Read the given line separated json file and turn it into a data frame.

    :param path: The path to the json file to process.
    :param columns: The fields to keep from the json.
      If given as a dictionary, use the keys as the column names
      in the final data frame.
      Individual fields are split by the key separator for nested accesses.
    :param prefix: The fields to prefix any access with.
      Useful when all interesting data is contained within a nested object.
      Split by the key separator for nested accesses.
    :param key_separator: The sub string that denotes that we are accessing
      a nested json object.

      - Example: With \".\", \"a.b\" gets turned into a nested access
        of first field `a` and then field `b`.
    :param filters: Filter functions to be applied to individual
      entries of the json file before they are collected.
    :param dropped_values: A mapping from field name to a collection of
      values that shall be dropped from entries with that field.
    :param remapped_values: A mapping from field name to a dictionary
      that describes re-mappings of values within that field.
    :param max_len: The maximum number of entries to read from the json.
    :returns: The resulting data, as a pandas DataFrame.
    """
    return pd.DataFrame(
        _dicts_from_json_file(
            path.expanduser(),
            columns,
            key_separator=key_separator,
            prefix=prefix,
            filters=filters,
            dropped_values=dropped_values,
            remapped_values=remapped_values,
            max_len=max_len,
        ),
        columns=list(columns.keys() if isinstance(columns, dict) else columns),
    )


cached_uris: dict[str, str | None] = dict()


def labels_from_uris(
    uris: Iterable[str | Iterable[str] | None],
    multi_value: Optional[bool] = None,
    label_seq: Sequence[str] = ("prefLabel", "de"),
) -> list[str | None] | list[list[str | None] | None]:
    """
    Get labels for the given URIs by looking up each URI.

    Note that this can be much slower than labels_from_skos,
    as each URI requires its own separate HTTP request.

    :param uris: The URIs to process.
    :param multi_value: Whether values in uris contain multiple URIs each.
        If None, this is determined automatically.
    :param label_seq: The sequence of fields to look up in the URI
        in order to get to the label to return.
    """
    if multi_value is None:
        for value in uris:
            if value is not None:
                multi_value = isinstance(value, Collection)
                break

    def uri_label(uri: str) -> Optional[str]:
        """Look up a URI and return its preferred label"""
        if not uri:
            return None

        # we want json, not html. some URIs default to html
        if ".html" == uri[-5:]:
            uri = uri[:-5]
        if ".json" != uri[-5:]:
            uri = uri + ".json"

        try:
            with requests.get(uri) as request:
                if request.ok:
                    concept = request.json()
                else:
                    return None

        # catch invalid results
        except Exception:
            return None

        return get_in(concept, label_seq)  # type: ignore

    def uri_to_label(uri: str) -> Optional[str]:
        """Return the preferred label of a URI, looking it up if necessary"""
        if uri in cached_uris:
            return cached_uris[uri]

        label = uri_label(uri)
        cached_uris[uri] = label
        return label

    if multi_value:
        return [
            [uri_to_label(uri) for uri in uri_values]
            if uri_values is not None
            else None
            for uri_values in uris
        ]

    return [
        uri_to_label(uri) if uri is not None else None for uri in uris  # type: ignore
    ]


def labels_from_skos(
    ids: Iterable[str | Iterable[str] | None],
    url: str,
    multi_value: Optional[bool] = None,
    label_seq: Sequence[str] = ("prefLabel", "de"),
    id_seq: Sequence[str] = ("id",),
) -> list[Basic_Value | None] | list[list[Basic_Value] | None]:
    """
    Get URIs for the given IDs by first reading a SKOS vocabulary.

    :param ids: The IDs within the vocabulary to look up.
    :param url: The URL of the SKOS vocabulary to read.
    :param multi_value: Whether values in ids contain multiple IDs each.
        If None, this is determined automatically.
    :param label_seq: The sequence of fields to look up in the SKOS vocab
        in order to get to the label to return.
    :param id_seq: The sequence of fields to look up the ID in the SKOS vocab
        in order to link to the given IDs.
    """
    with requests.get(url) as request:
        schema: Data_Point = request.json()

    # dictionary mapping ids to labels
    labels = _get_label_dict(schema, label_seq, id_seq)

    if multi_value is None:
        for value in ids:
            if value is not None:
                multi_value = isinstance(value, Collection)
                break

    if multi_value:
        fun_multi = lambda x: [labels[value] for value in x] if x is not None else None
        return [fun_multi(id) for id in ids]

    else:
        fun_single = lambda x: labels[x] if x is not None else None
        return [fun_single(id) for id in ids]


def hierarchy_from_skos(
    url: str,
    id_seq: Sequence[str] = ("id",),
    label_seq: Sequence[str] = ("prefLabel", "de"),
    subcategory_fields: Collection[str] = frozenset({"narrower", "hasTopConcept"}),
) -> list[dict[str, Basic_Value]]:
    """
    Get the map from IDs to parent for a remote schema.

    :param id_seq: The sequence of fields to look up the ID in the schema
        in order to link to the given IDs.
    :param label_seq: The sequence of fields to look up in the schema
        in order to get to the label to return.
    :param subcategory_fields: The possible fields in the schema
        that contain a parent's children.
    """
    with requests.get(url) as request:
        schema = request.json()

    child_map = get_children_map(
        schema, id_seq=id_seq, subcategory_fields=subcategory_fields
    )
    parent_map = defaultdict(lambda: None) | get_parent_map(child_map)
    labels = _get_label_dict(schema, id_seq=id_seq, label_seq=label_seq)

    return [
        {"name": label, "key": key, "parent": parent_map[key]}
        for key, label in labels.items()
    ]


def _get_label_dict(
    schema: Data_Point, label_seq: Sequence[str], id_seq: Sequence[str]
) -> dict[Basic_Value, Basic_Value]:
    """Get a map from id's to labels, from the given schema"""
    labels: dict[Basic_Value, Basic_Value] = defaultdict(lambda: None)
    for leaf in get_leaves(schema):
        n = len(label_seq)
        if len(leaf) < len(label_seq) or leaf[-n:] != label_seq:
            continue

        hit_label = get_terminal_in(schema, leaf)
        hit_id = get_terminal_in(schema, leaf[:-n] + tuple(id_seq))

        # we found nested sub-trees
        if isinstance(hit_label, list):
            if isinstance(hit_id, list):
                labels.update({id: label for id, label in zip(hit_id, hit_label)})
            else:
                labels.update({hit_id: label for label in hit_label})

            continue

        if isinstance(hit_id, list):
            labels.update({id: hit_label for id in hit_id})
        else:
            labels.update({hit_id: hit_label})

    return labels

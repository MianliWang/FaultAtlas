from importlib.metadata import metadata, version

import faultatlas


def test_package_version_comes_from_distribution_metadata() -> None:
    assert faultatlas.__version__ == version("faultatlas")


def test_distribution_name_is_faultatlas() -> None:
    assert metadata("faultatlas")["Name"] == "faultatlas"

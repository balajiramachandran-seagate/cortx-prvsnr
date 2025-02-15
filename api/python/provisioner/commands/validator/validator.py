#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#
import logging
from abc import abstractmethod, ABC
from hmac import compare_digest
from pathlib import Path
from typing import Dict, Callable, Optional, Union, Type

from ... import utils
from ...config import ContentType, HashType

from ...vendor import attr
from ...errors import ValidationError

logger = logging.getLogger(__name__)


class PathValidator(ABC):

    """Abstract Path Validator class defines the interface for inheritance."""

    @abstractmethod
    def validate(self, path: Path):
        """
        Abstract validation method of Validator.

        Parameters
        ----------
        path: Path
            path for file validation


        Returns
        -------
        None

        Raises
        ------
        ValidationError
            If validation is failed.
        """
        pass

    def __call__(self, *args, **kwargs):
        """
        Call-wrapper over self.validate method. It adds function-like behavior
        for all class instances.

        Parameters
        ----------
        args:
            tuple of all positional arguments
        kwargs:
            dict with all keyword arguments

        Returns
        -------
        None

        Raises
        ------
        ValidationError
            If validation is failed.
        """
        self.validate(*args, **kwargs)


@attr.s(auto_attribs=True)
class FileValidator(PathValidator):

    """
    Class for file validation.

    Attributes
    ----------
    required: bool
        if True validation raises an Exception if the file doesn't exist
    content_validator: Optional[Callable[[Path], None]]
        callable object for file content validation.

        Should raise the `ValidationError` exception if file content validation
        is failed

    Notes
    -----
    TBD: other possible parameters
        permissions: int/str
            requested file permissions
        owner: str
            requested file owner
        group: str
            requested file group
        is_symlink: bool
            defines if file should be a symlink

    At initialization time `attr.s` is responsible for `_required`
    and `_content_validator` attributes validation.
    """

    required: bool = attr.ib(
        validator=attr.validators.instance_of(bool),
        default=False
    )
    content_validator: Optional[Callable[[Path], None]] = attr.ib(
        init=False,
        validator=attr.validators.optional(attr.validators.is_callable()),
        default=None,
    )

    def validate(self, path: Path):
        """
        Validate the file by a given path.

        Parameters
        ----------
        path: Path
            path for file validation

        Returns
        -------
        None

        Raises
        ------
        ValidationError
            If validation is failed.

        """
        logger.debug(f"Start '{path}' file validation")

        if not path.exists():
            if self.required:
                raise ValidationError(reason=f"File '{path}' should exist.")
            return

        logger.debug(f"File '{path}' exists.")

        if not path.is_file():
            raise ValidationError(reason=f"'{path}' is not a regular file.")

        if self.content_validator:
            # Should raise an Exception if validation fails
            self.content_validator(path)  # pylint: disable=not-callable


@attr.s(auto_attribs=True)
class DirValidator(PathValidator):

    """
    Class for catalog validation.

    Attributes
    ----------
    files_scheme: Optional[Dict]
        Nested catalog structure for the validation path

    required: bool
        if True validation raises an Exception if the directory
        doesn't exist

    Notes
    -----
    TBD: other possible parameters
    permissions: int/str
        requested directory permissions
    owner: str
        requested directory owner
    group: str
        requested directory group

    At initialization time `attr.s` is responsible for `_file_scheme`
    validation and converting keys of file scheme from string to `Path`
    instance.
    """

    files_scheme: Optional[Dict] = attr.ib(
        validator=attr.validators.optional(
            attr.validators.deep_mapping(
                key_validator=attr.validators.instance_of((str, Path)),
                value_validator=attr.validators.instance_of(PathValidator),
                mapping_validator=attr.validators.instance_of(dict)
            )
        ),
        converter=utils.converter_file_scheme_key,
        default=None,
    )
    required: bool = attr.ib(
        validator=attr.validators.instance_of(bool),
        default=False
    )

    def validate(self, path: Path):
        """
        Validate the directory by a given path.

        Parameters
        ----------
        path: Path
            path for file validation

        Returns
        -------
        None

        Raises
        ------
        ValidationError
            If validation is failed.
        """
        logger.debug(f"Start '{path}' directory validation")

        if not path.exists():
            if self.required:
                raise ValidationError(reason=f"File '{path}' should exist.")
            return

        logger.debug(f"Directory '{path}' exists.")

        if not path.is_dir():
            raise ValidationError(reason=f"'{path}' is not a directory")

        if self.files_scheme:
            for sub_path, validator in self.files_scheme.items():
                validator.validate(path / sub_path)


@attr.s(auto_attribs=True)
class FileSchemeValidator(PathValidator):

    """
    Scheme Validator for files and directories.

    Attributes
    ----------
    scheme: Optional[Dict]
        dictionary with files scheme

    Notes
    -----
    At initialization time `attr.s` is responsible for `_scheme` validation
    and converting keys of file scheme from string to `Path` instance.
    """

    scheme: Optional[Dict] = attr.ib(
        validator=attr.validators.optional(
            attr.validators.deep_mapping(
                key_validator=attr.validators.instance_of((str, Path)),
                value_validator=attr.validators.instance_of(PathValidator),
                mapping_validator=attr.validators.instance_of(dict)
            )
        ),
        converter=utils.converter_file_scheme_key,
        default=None
    )

    def validate(self, path: Path):
        """
        Validate the catalog structure against validation scheme for given
        path

        Parameters
        ----------
        path: Path
            path for catalog scheme validation

        Returns
        -------
        None

        Raises
        ------
        ValidationError
            If validation is failed.
        """
        for sub_path, validator in self.scheme.items():
            validator.validate(path / sub_path)


class YumRepoDataValidator(DirValidator):

    """Special alias for yum repo data validation."""

    def __init__(self):
        super().__init__({Path("repomd.xml"): FileValidator(required=True)},
                         required=True)


@attr.s
class HashSumValidator(FileValidator):

    """
    Validator of hash-sum for the provided file and expected hash-sum for this
    file.

    Attributes
    ----------
    hash_sum: Union[str, bytes, bytearray]
        Hexadecimal string or byte-array object with expected hash-sum value
        of validated file.
    hash_type: HashType
        Type of hash sum. See `Hashtype` for more information

    """
    hash_sum: Union[str, bytes, bytearray] = attr.ib(
        validator=attr.validators.instance_of((str, bytes, bytearray)),
        converter=lambda x: bytes.fromhex(x) if isinstance(x, str) else x,
        default=None
    )
    hash_type: HashType = attr.ib(
        validator=attr.validators.in_(HashType),
        default=HashType.MD5,
        converter=lambda x: HashType.MD5 if x is None else HashType(x)
    )

    def validate(self, path: Path):
        """
        Validates if hash-sum of the file provided by `path` matches
        the attribute value of `_hash_sum`.

        Parameters
        ----------
        path: Path
            path to the file which hash-sum will be validated

        Returns
        -------
        None

        Raises
        ------
        ValidationError
            If validation is failed.
        """
        super().validate(path)

        hash_obj = utils.calc_hash(path, self.hash_type)

        # hash_obj here is an object returned by `hashlib`
        # python istandard library module so we compare against
        # one provided by a caller
        if not compare_digest(hash_obj.digest(), self.hash_sum):
            raise ValidationError(
                    f"Hash sum of file '{path}': '{hash_obj.hexdigest()}' "
                    f"mismatches the provided one '{self.hash_sum.hex()}'")


@attr.s(auto_attribs=True)
class FileContentScheme:

    """
    Abstract file scheme class.

    It can be used to define an abstract interface if necessary.
    Also it is useful to have the parent class for all file schemes inherited
    from this one for comparison using `isinstance`, `type` and for `attr`
    module.

    Attributes
    ----------
    _unexpected_attributes: dict
        Stores all attribute values that were not listed
        in the class definition.

        Note: This attribute will be useful in the implementation of logic
        if we need to validate that some attributes should not be listed
        in the data scheme.
    """

    def set_unexpected_attributes(self, args: dict):
        self._unexpected_attrs = args

    def get_unexpected_attributes(self):
        return getattr(self, "_unexpected_attrs", None)

    _unexpected_attributes = property(get_unexpected_attributes,
                                      set_unexpected_attributes)

    @classmethod
    def from_args(cls, data: Union[list, dict]):
        unexpected_attrs = dict()
        if isinstance(data, dict):
            # TODO: it is good to make copy of input data parameter
            for _attr in (data.keys() - set(a for a in attr.fields_dict(cls))):
                # NOTE: Remove unexpected attributes from initialization `data`
                #  dictionary
                unexpected_attrs[_attr] = data.pop(_attr)

            # If some attributes are missed in `data`, the `attr` module is
            #  responsible for that validation
            obj = cls(**data)
            obj._unexpected_attributes = unexpected_attrs
            return obj
        elif isinstance(data, list):
            obj = cls(*data)
            obj._unexpected_attributes = unexpected_attrs
            return obj
        else:
            raise ValidationError("Unexpected top-level content type: "
                                  f"'{type(data)}'")


@attr.s(auto_attribs=True)
class ReleaseInfoContentScheme(FileContentScheme):

    """
    RELEASE.INFO file content scheme.

    This class is used for `RELEASE.INFO` file content validation.

    Attributes
    ----------
    NAME: str
        Name of SW upgrade repository. It is the `NAME` field of `RELEASE.INFO`
        file
    RELEASE: Optional[str]
        Release of SW upgrade repository. Can be absent. It is the `RELEASE`
        field of `RELEASE.INFO` file
    VERSION: str
        Version number of SW upgrade repository. It is the `VERSION` field of
        `RELEASE.INFO` file
    BUILD: str
        Build number of SW upgrade repository. It is the `BUILD` field of
        `RELEASE.INFO` file
    OS: str
        OS version for which this SW upgrade repo is intended.
        It is the `OS` field of `RELEASE.INFO` file
    COMPONENTS: list
        List of RPMs provided by this SW upgrade repository.
        It is the `COMPONENTS` field of `RELEASE.INFO` file
    """

    NAME: str = attr.ib(
        validator=attr.validators.instance_of(str)
    )
    VERSION: str = attr.ib(
        # regex is based on the current representation of `RELEASE` field
        # number. It is 3 numbers divided by dots "."
        validator=attr.validators.matches_re("^[0-9]+\.[0-9]+\.[0-9]+$"),
        converter=str
    )
    BUILD: str = attr.ib(
        # regex is based on the current representation of `BUILD` number.
        # It is 1 or more numbers
        validator=attr.validators.matches_re("^[0-9]+$"),
        converter=str
    )
    OS: str = attr.ib(
        validator=attr.validators.instance_of(str)
    )
    COMPONENTS: list = attr.ib(
        validator=attr.validators.instance_of(list)
    )
    RELEASE: Optional[str] = attr.ib(
        # TODO: when the `RELEASE` field will be introduced need to use here
        #  a proper regex validation
        validator=attr.validators.optional(
            attr.validators.instance_of(str)
        ),
        default=None
    )


@attr.s(auto_attribs=True)
class ContentFileValidator(PathValidator):

    """
    Class implements the basic logic of file content validation.

    Attributes
    ----------
    scheme: Type[FileContentScheme]
        File content scheme for validation.

    content_type: ContentType
        Content type of the file. `ContentType.YAML` is default value

    """

    scheme: Type[FileContentScheme] = attr.ib(
        validator=utils.validator__subclass_of(FileContentScheme)
    )
    content_type: ContentType = attr.ib(
        validator=attr.validators.in_(ContentType),
        default=ContentType.YAML
    )

    _CONTENT_LOADER = {
        ContentType.YAML: utils.load_yaml,
        ContentType.JSON: utils.load_json,
    }

    def validate(self, path: Path):
        """
        Validates the file content of the provided `path`.

        Parameters
        ----------
        path: Path
            File path for content validation

        Returns
        -------
        None

        Raises
        ------
        ValidationError
            If validation is failed.
        """
        try:
            logging.debug(f"File content type: '{self.content_type}'")
            content = self._CONTENT_LOADER[self.content_type](path)
        except Exception as e:
            raise ValidationError(
                            f"File content validation is failed: {e}") from e

        logging.debug(f"File content: '{content}'")
        try:
            self.scheme.from_args(content)
        except TypeError as e:
            raise ValidationError(f"File content validation is failed: {e}")
        else:
            logging.info(f"File content validation is succeeded for '{path}'")


@attr.s(auto_attribs=True)
class ReleaseInfoValidator(FileValidator):

    """
    Special alias for `RELEASE.INFO` file validator.

    Attributes
    ----------
    required: bool
        if `True` validation raises an Exception if the file doesn't exist.
        `True` by default
    content_type: ContentType
        Content type of the `RELEASE.INFO` file.
        `ContentType.YAML` is default value
    """

    required: bool = attr.ib(
        validator=attr.validators.instance_of(bool),
        # NOTE: it is a difference in comparison of `FileValidator`
        default=True
    )
    content_type: ContentType = attr.ib(
        validator=attr.validators.in_(ContentType),
        default=ContentType.YAML
    )

    def __attrs_post_init__(self):
        self.content_validator = ContentFileValidator(
                scheme=ReleaseInfoContentScheme,
                content_type=self.content_type)

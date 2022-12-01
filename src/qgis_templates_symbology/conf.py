# -*- coding: utf-8 -*-
"""
    Handles storage and retrieval of the plugin QgsSettings.
"""

import contextlib
import dataclasses
import datetime
import enum
import typing
import uuid

from qgis.PyQt import (
    QtCore,
    QtWidgets,
)
from qgis.core import QgsRectangle, QgsSettings

from .models import Template, Symbology


@contextlib.contextmanager
def qgis_settings(group_root: str, settings=None):
    """Context manager to help defining groups when creating QgsSettings.

    :param group_root: Name of the root group for the settings.
    :type group_root: str

    :param settings: QGIS settings to use
    :type settings: QgsSettings

    :yields: Instance of the created settings.
    :type: QgsSettings
    """
    if settings is None:
        settings = QgsSettings()
    settings.beginGroup(group_root)
    try:
        yield settings
    finally:
        settings.endGroup()


@dataclasses.dataclass
class ProfileSettings:
    """Manages the plugin profile settings.
    """

    id: uuid.UUID
    name: str
    path: str
    templates: list
    symbology: list
    created_date: datetime.datetime = datetime.datetime.now()

    @classmethod
    def from_qgs_settings(
            cls,
            identifier: str,
            settings: QgsSettings):
        """Reads QGIS settings and parses them into a profile
        settings instance with the respective settings values as properties.

        :param identifier: Profile identifier
        :type identifier: str

        :param settings: QGIS settings.
        :type settings: QgsSettings

        :returns: Profile settings object
        :rtype: ProfileSettings
        """
        templates = []
        symbology = []
        try:
            templates = settings_manager.get_templates(
                uuid.UUID(identifier)
            )
            symbology = settings_manager.get_symbology(
                uuid.UUID(identifier)
            )

            created_date = datetime.datetime.strptime(
                settings.value("created_date"),
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ) if settings.value("created_date") is not None else None
        except AttributeError:
            created_date = datetime.datetime.now()

        return cls(
            id=uuid.UUID(identifier),
            name=settings.value("name"),
            path=settings.value("path"),
            templates=templates,
            symbology=symbology,
            created_date=created_date,
        )


@dataclasses.dataclass
class TemplateSettings(Template):
    """Plugin template setting
    """

    @classmethod
    def from_qgs_settings(
            cls,
            identifier: str,
            settings: QgsSettings):
        """Reads QGIS settings and parses them into a template

        :param identifier: Template identifier
        :type identifier: str

        :param settings: QGIS settings.
        :type settings: QgsSettings

        :returns: Templates settings object
        :rtype: TemplateSettings
        """

        return cls(
            name=settings.value("name", None),
            id=settings.value("id", None),
        )


@dataclasses.dataclass
class SymbologySettings(Symbology):
    """Plugin template setting
    """

    @classmethod
    def from_qgs_settings(
            cls,
            identifier: str,
            settings: QgsSettings):
        """Reads QGIS settings and parses them into a symbology
        settings instance with the respective settings values as properties.

        :param identifier: Symbology identifier
        :type identifier: str

        :param settings: QGIS settings.
        :type settings: QgsSettings

        :returns: Symbology settings object
        :rtype: SymbologySettings
        """

        return cls(
            name=settings.value("name", None),
            id=settings.value("id", None),
        )


class SettingsManager(QtCore.QObject):
    """Manages saving/loading settings for the plugin in QgsSettings.
    """

    BASE_GROUP_NAME: str = "qgis_templates_symbology"
    PROFILE_GROUP_NAME: str = "profiles"
    SELECTED_PROFILE_KEY: str = "selected_profile"
    TEMPLATE_GROUP_NAME: str = "templates"
    SYMBOLOGY_GROUP_NAME: str = "symbology"

    settings = QgsSettings()

    profiles_settings_updated = QtCore.pyqtSignal()

    def set_value(self, name: str, value):
        """Adds a new setting key and value on the plugin specific settings.

        :param name: Name of setting key
        :type name: str

        :param value: Value of the setting
        :type value: Any

        """
        self.settings.setValue(
            f"{self.BASE_GROUP_NAME}/{name}",
            value
        )

    def get_value(
            self,
            name: str,
            default=None,
            setting_type=None):
        """Gets value of the setting with the passed name.

        :param name: Name of the setting key
        :type name: str

        :param default: Default value returned when the
         setting key does not exist
        :type default: Any

        :param setting_type: Type of the store setting
        :type setting_type: Any

        :returns: Value of the setting
        :rtype: Any
        """
        if setting_type:
            return self.settings.value(
                f"{self.BASE_GROUP_NAME}/{name}",
                default,
                setting_type
            )
        return self.settings.value(
            f"{self.BASE_GROUP_NAME}/{name}",
            default
        )

    def remove(self, name):
        """Remove the setting with the specified name.

        :param name: Name of the setting key
        :type name: str
        """
        self.settings.remove(
            f"{self.BASE_GROUP_NAME}/{name}"
        )

    def list_profiles(self) -> typing.List[ProfileSettings]:
        """Lists all the plugin profiles stored in the QgsSettings.

        :return: Plugin profiles
        :rtype: List[ProfileSettings]
        """
        result = []
        with qgis_settings(
                f"{self.BASE_GROUP_NAME}/"
                f"{self.PROFILE_GROUP_NAME}") \
                as settings:
            for profile_id in settings.childGroups():
                profile_settings_key = self._get_profile_settings_base(
                    profile_id
                )
                with qgis_settings(profile_settings_key) \
                        as profile_settings:
                    result.append(
                        ProfileSettings.from_qgs_settings(
                            profile_id, profile_settings
                        )
                    )
        return result

    def delete_all_profiles(self):
        """Deletes all the plugin profiles settings in QgsSettings.
        """
        with qgis_settings(
                f"{self.BASE_GROUP_NAME}"
                f"/{self.PROFILE_GROUP_NAME}") \
                as settings:
            for profile_name in settings.childGroups():
                settings.remove(profile_name)
        self.clear_current_profile()
        self.profiles_settings_updated.emit()

    def find_profile_by_name(self, name):
        """Finds a profile setting inside the plugin QgsSettings by name.

        :param name: Name of the profile
        :type: str

        :returns: Profile settings instance
        :rtype: ProfileSettings
        """
        with qgis_settings(
                f"{self.BASE_GROUP_NAME}/"
                f"{self.PROFILE_GROUP_NAME}") \
                as settings:
            for profile_id in settings.childGroups():
                profile_settings_key = self._get_profile_settings_base(
                    profile_id
                )
                with qgis_settings(profile_settings_key) \
                        as profile_settings:
                    profile_name = profile_settings.value("name")
                    if profile_name == name:
                        found_id = uuid.UUID(profile_id)
                        break
            else:
                raise ValueError(
                    f"Could not find a profile named "
                    f"{name!r} in QgsSettings"
                )
        return self.get_profile_settings(found_id)

    def get_profile_settings(
            self,
            identifier: uuid.UUID) -> ProfileSettings:
        """Gets the profile setting with the specified identifier.

        :param identifier: Profile identifier
        :type identifier: uuid.UUID

        :returns: Profile settings instance
        :rtype: ProfileSettings
        """
        settings_key = self._get_profile_settings_base(identifier)
        with qgis_settings(settings_key) as settings:
            profile_settings = ProfileSettings.from_qgs_settings(
                str(identifier), settings
            )
        return profile_settings

    def save_profile_settings(
            self,
            profile_settings: ProfileSettings):
        """Saves profile settings from the given profile object.

        :param profile_settings: Profile settings object
        :type profile_settings: ProfileSettings

        """
        settings_key = self._get_profile_settings_base(
            profile_settings.id
        )
        created_date = profile_settings.created_date.\
            strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        if profile_settings.templates:
            for template in profile_settings.templates:
                self.save_template(
                    profile_settings,
                    template
                )
        if profile_settings.symbology:
            for symbology in profile_settings.symbology:
                self.save_symbology(
                    profile_settings,
                    symbology
                )
        with qgis_settings(settings_key) as settings:
            settings.setValue("name", profile_settings.name)
            settings.setValue("path", profile_settings.path)
            settings.setValue("created_date", created_date)
        self.profiles_settings_updated.emit()

    def delete_profile(self, identifier: uuid.UUID):
        """Deletes plugin profile that match the passed identifier.

        :param identifier: Profile identifier
        :type identifier: uuid.UUID
        """
        if self.is_current_profile(identifier):
            self.clear_current_profile()
        with qgis_settings(
                f"{self.BASE_GROUP_NAME}/"
                f"{self.PROFILE_GROUP_NAME}")\
                as settings:
            settings.remove(str(identifier))
        self.profiles_settings_updated.emit()

    def get_current_profile(self) -> typing.Optional[ProfileSettings]:
        """Gets the current active profile from the QgsSettings.

        :returns Profile settings instance
        :rtype ProfileSettings

        """
        with qgis_settings(self.BASE_GROUP_NAME) as settings:
            current = settings.value(self.SELECTED_PROFILE_KEY)
        if current is not None:
            result = self.get_profile_settings(uuid.UUID(current))
        else:
            result = None
        return result

    def get_latest_profile(self) -> typing.Optional[ProfileSettings]:
        """Gets the most recent added profile from the QgsSettings.

        :returns Profile settings instance
        :rtype ProfileSettings

        """
        profile_list = self.list_profiles()
        if len(profile_list) < 1:
            return None
        latest_profile = profile_list[0]

        for profile in profile_list:
            if profile.created_date > latest_profile.created_date:
                latest_profile = profile

        return latest_profile

    def set_current_profile(self, identifier: uuid.UUID):
        """Updates the plugin settings and set the profile with the
           passed identifier as the selected profile.

        :param identifier: Profile identifier
        :type identifier: uuid.UUID
        """
        if identifier not in [profile.id for profile in self.list_profiles()]:
            raise ValueError(f"Invalid profile identifier: {id!r}")
        serialized_id = str(identifier)
        with qgis_settings(self.BASE_GROUP_NAME) as settings:
            settings.setValue(self.SELECTED_PROFILE_KEY, serialized_id)
        self.profiles_settings_updated.emit()

    def clear_current_profile(self):
        """Removes the current selected profile in the settings.
        """
        with qgis_settings(self.BASE_GROUP_NAME) as settings:
            settings.setValue(self.SELECTED_PROFILE_KEY, None)
        self.profiles_settings_updated.emit()

    def is_current_profile(self, identifier: uuid.UUID):
        """Checks if the profile with the passed identifier
            is the current selected profile.

        :param identifier: Profile settings identifier.
        :type identifier: uuid.UUID
        """
        current = self.get_current_profile()
        return False if current is None else current.id == identifier

    def is_profile(self, identifier: uuid.UUID):
        """Checks if the profile with the identifier exists

        :param identifier: Profile settings identifier.
        :type identifier: uuid.UUID
        """
        profiles = self.list_profiles()
        exists = any([profile.id == identifier for profile in profiles])
        return exists

    def _get_profile_settings_base(
            self,
            identifier: typing.Union[str, uuid.UUID]):
        """Gets the profile settings base url.

        :param identifier: Profile settings identifier
        :type identifier: uuid.UUID

        :returns Profile settings base group
        :rtype str
        """
        return f"{self.BASE_GROUP_NAME}/" \
               f"{self.PROFILE_GROUP_NAME}/" \
               f"{str(identifier)}"


    def _get_template_settings_base(
            self,
            profile_identifier,
            identifier
    ):
        """Gets the template settings base url.

        :param profile_identifier: Profile settings identifier
        :type profile_identifier: uuid.UUID

        :param identifier: Template settings identifier
        :type identifier: uuid.UUID

        :returns Template settings base group
        :rtype str
        """
        return f"{self.BASE_GROUP_NAME}/" \
               f"{self.PROFILE_GROUP_NAME}/" \
               f"{str(profile_identifier)}/" \
               f"{self.TEMPLATE_GROUP_NAME}/" \
               f"{str(identifier)}"


    def save_template(self, profile, template_settings):
        """ Save the passed template settings into the plugin settings

        :param profile: Profile settings
        :type profile:  TemplateSettings

        :param template_settings: Template settings
        :type template_settings:  TemplateSettings
        """
        settings_key = self._get_template_settings_base(
            profile.id,
            template_settings.id
        )

        with qgis_settings(settings_key) as settings:
            settings.setValue("name", template_settings.name)
            settings.setValue("id", template_settings.id)

    def get_templates(self, profile_identifier):
        """ Gets all the available templates settings in the
        provided profile

        :param profile_identifier: Profile identifier
        :type profile_identifier: uuid.UUID

        :returns List of the template settings instances
        :rtype list
        """
        result = []
        with qgis_settings(
                f"{self.BASE_GROUP_NAME}/"
                f"{self.PROFILE_GROUP_NAME}/"
                f"{str(profile_identifier)}/"
                f"{self.TEMPLATE_GROUP_NAME}"
        ) \
                as settings:
            for uuid in settings.childGroups():
                template_settings_key = self._get_template_settings_base(
                    profile_identifier,
                    uuid
                )
                with qgis_settings(template_settings_key) \
                        as template_settings:
                    result.append(
                        TemplateSettings.from_qgs_settings(
                            uuid, template_settings
                        )
                    )
        return result

    def _get_symbology_settings_base(
            self,
            profile_identifier,
            identifier
    ):
        """Gets the symbology settings base url.

        :param profile_identifier: Profile settings identifier
        :type profile_identifier: uuid.UUID

        :param identifier: Symbology settings identifier
        :type identifier: uuid.UUID

        :returns Template settings base group
        :rtype str
        """
        return f"{self.BASE_GROUP_NAME}/" \
               f"{self.PROFILE_GROUP_NAME}/" \
               f"{str(profile_identifier)}/" \
               f"{self.SYMBOLOGY_GROUP_NAME}/" \
               f"{str(identifier)}"


    def save_symbology(self, profile, symbology_settings):
        """ Save the passed symbology settings into the plugin settings

        :param profile: Profile settings
        :type profile:  SymbologySettings

        :param symbology_settings: Symbology settings
        :type symbology_settings:  SymbologySettings
        """
        settings_key = self._get_symbology_settings_base(
            profile.id,
            symbology_settings.id
        )

        with qgis_settings(settings_key) as settings:
            settings.setValue("name", symbology_settings.name)
            settings.setValue("id", symbology_settings.id)
            
    
    def get_symbology(self, profile_identifier):
        """ Gets all the available symbology settings in the
        provided profile

        :param profile_identifier: Profile identifier
        :type profile_identifier: uuid.UUID

        :returns List of the symbology settings instances
        :rtype list
        """
        result = []
        with qgis_settings(
                f"{self.BASE_GROUP_NAME}/"
                f"{self.PROFILE_GROUP_NAME}/"
                f"{str(profile_identifier)}/"
                f"{self.SYMBOLOGY_GROUP_NAME}"
        ) \
                as settings:
            for uuid in settings.childGroups():
                symbology_settings_key = self._get_symbology_settings_base(
                    profile_identifier,
                    uuid
                )
                with qgis_settings(symbology_settings_key) \
                        as symbology_settings:
                    result.append(
                        SymbologySettings.from_qgs_settings(
                            uuid, symbology_settings
                        )
                    )
        return result


settings_manager = SettingsManager()

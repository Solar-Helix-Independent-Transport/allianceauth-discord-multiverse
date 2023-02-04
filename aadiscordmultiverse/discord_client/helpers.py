from copy import copy
from typing import Set, Iterable


class DiscordRoles:
    """Container class that helps dealing with Discord roles.

    Objects of this class are immutable and work in many ways like sets.

    Ideally objects are initialized from raw API responses,
    e.g. from DiscordClient.guild.roles()
    """
    _ROLE_NAME_MAX_CHARS = 100

    def __init__(self, roles_lst: list) -> None:
        """roles_lst must be a list of dict, each defining a role"""
        if not isinstance(roles_lst, (list, set, tuple)):
            raise TypeError('roles_lst must be of type list, set or tuple')
        self._roles = dict()
        self._roles_by_name = dict()
        for role in list(roles_lst):
            self._assert_valid_role(role)
            self._roles[int(role['id'])] = role
            self._roles_by_name[self.sanitize_role_name(role['name'])] = role

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self.ids() == other.ids()
        return NotImplemented

    def __hash__(self):
        return hash(tuple(sorted(self._roles.keys())))

    def __iter__(self):
        yield from self._roles.values()

    def __contains__(self, item) -> bool:
        return int(item) in self._roles

    def __len__(self):
        return len(self._roles.keys())

    def has_roles(self, role_ids: Set[int]) -> bool:
        """returns true if this objects contains all roles defined by given role_ids
        incl. managed roles
        """
        role_ids = {int(id) for id in role_ids}
        all_role_ids = self._roles.keys()
        return role_ids.issubset(all_role_ids)

    def ids(self) -> Set[int]:
        """return a set of all role IDs"""
        return set(self._roles.keys())

    def subset(
        self,
        role_ids: Iterable[int] = None,
        managed_only: bool = False,
        role_names: Iterable[str] = None
    ) -> "DiscordRoles":
        """returns a new object containing the subset of roles

        Args:
        - role_ids: role ids must be in the provided list
        - managed_only: roles must be managed
        - role_names: role names must match provided list (not case sensitive)
        """
        if role_ids is not None:
            role_ids = {int(id) for id in role_ids}

        if role_ids is not None and not managed_only:
            return type(self)([
                role for role_id, role in self._roles.items() if role_id in role_ids
            ])

        elif role_ids is None and managed_only:
            return type(self)([
                role for _, role in self._roles.items() if role['managed']
            ])

        elif role_ids is not None and managed_only:
            return type(self)([
                role for role_id, role in self._roles.items()
                if role_id in role_ids and role['managed']
            ])

        elif role_ids is None and managed_only is False and role_names is not None:
            role_names = {self.sanitize_role_name(name).lower() for name in role_names}
            return type(self)([
                role for role in self._roles.values()
                if role["name"].lower() in role_names
            ])

        return copy(self)

    def union(self, other: object) -> "DiscordRoles":
        """returns a new roles object that is the union of this roles object
        with other"""
        return type(self)(list(self) + list(other))

    def difference(self, other: object) -> "DiscordRoles":
        """returns a new roles object that only contains the roles
        that exist in the current objects, but not in other
        """
        new_ids = self.ids().difference(other.ids())
        return self.subset(role_ids=new_ids)

    def role_by_name(self, role_name: str) -> dict:
        """returns role if one with matching name is found else an empty dict"""
        role_name = self.sanitize_role_name(role_name)
        if role_name in self._roles_by_name:
            return self._roles_by_name[role_name]
        return dict()

    @classmethod
    def create_from_matched_roles(cls, matched_roles: list) -> "DiscordRoles":
        """returns a new object created from the given list of matches roles

        matches_roles must be a list of tuples in the form: (role, created)
        """
        raw_roles = [x[0] for x in matched_roles]
        return cls(raw_roles)

    @staticmethod
    def _assert_valid_role(role: dict) -> None:
        if not isinstance(role, dict):
            raise TypeError('Roles must be of type dict: %s' % role)

        if 'id' not in role or 'name' not in role or 'managed' not in role:
            raise ValueError('This role is not valid: %s' % role)

    @classmethod
    def sanitize_role_name(cls, role_name: str) -> str:
        """shortens too long strings if necessary"""
        return str(role_name)[:cls._ROLE_NAME_MAX_CHARS]


def match_or_create_roles_from_names(
    client: object, guild_id: int, role_names: list
) -> DiscordRoles:
    """Shortcut for getting the result of matching role names as DiscordRoles object"""
    return DiscordRoles.create_from_matched_roles(
        client.match_or_create_roles_from_names(
            guild_id=guild_id, role_names=role_names
        )
    )

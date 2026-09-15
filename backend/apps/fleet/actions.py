"""
The catalog of things a bulk job may do.

Free-form shell is deliberately absent here. A job carries a catalog *key*; the
command is built in this module from a fixed template, and anything the caller
supplied reaches the shell only through ``shlex.quote``. The single-node
``POST /nodes/<pk>/run/`` endpoint remains the escape hatch for one-off shell,
where one operator is on the hook for one machine.
"""

import shlex
from dataclasses import dataclass

from django.conf import settings

from fleet.utils.exceptions import FleetError


class FleetActionUnknown(FleetError):
    """No such key in the catalog."""


class FleetActionInvalidParams(FleetError):
    """The supplied params do not match what the action declares."""


@dataclass(frozen=True)
class ActionParam:
    name: str
    description: str
    required: bool = False
    default: str | int | None = None
    choices: tuple[str, ...] = ()

    def resolve(self, params: dict):
        if self.name in params and params[self.name] not in (None, ""):
            value = params[self.name]
        elif self.required:
            raise FleetActionInvalidParams(f"Missing required parameter {self.name!r}")
        else:
            value = self.default

        if self.choices and str(value) not in self.choices:
            raise FleetActionInvalidParams(f"{self.name!r} must be one of {', '.join(self.choices)} — got {value!r}")
        return value

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "required": self.required,
            "default": self.default,
            "choices": list(self.choices),
        }


@dataclass(frozen=True)
class FleetAction:
    """
    One entry in the catalog.

    ``template`` is a ``str.format`` template whose placeholders are either a
    declared param or a server-side value (see :func:`_server_values`). Callers
    never reach the latter: unknown keys in the request are rejected before
    substitution happens.
    """

    name: str
    title: str
    description: str
    template: str
    params: tuple[ActionParam, ...] = ()
    timeout: float | None = None
    # Interrupts the gateway or the machine. The UI is expected to confirm these
    # separately; the API does not treat them differently.
    is_disruptive: bool = False

    def build(self, params: dict | None = None) -> str:
        params = params or {}

        declared = {param.name for param in self.params}
        unknown = sorted(set(params) - declared)
        if unknown:
            raise FleetActionInvalidParams(f"{self.name!r} accepts no parameter(s): {', '.join(unknown)}")

        values = {param.name: shlex.quote(str(param.resolve(params))) for param in self.params}
        # Applied last, so a param can never shadow a server-side value.
        values.update(_server_values())

        return self.template.format(**values)

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "params": [param.as_dict() for param in self.params],
            "timeout": self.timeout,
            "is_disruptive": self.is_disruptive,
        }


def _server_values() -> dict:
    """Substitutions the server owns. Read at build time so tests can override."""
    return {"gateway_service": shlex.quote(settings.FLEET_GATEWAY_SERVICE)}


ACTIONS: dict[str, FleetAction] = {
    action.name: action
    for action in (
        FleetAction(
            name="uptime",
            title="Uptime",
            description="How long the node has been up, and its load average.",
            template="uptime",
            timeout=30,
        ),
    )
}


def get_action(name: str) -> FleetAction:
    try:
        return ACTIONS[name]
    except KeyError:
        raise FleetActionUnknown(f"Unknown action {name!r}") from None


def build_command(name: str, params: dict | None = None) -> str:
    return get_action(name).build(params)


def catalog() -> list[dict]:
    return [action.as_dict() for action in ACTIONS.values()]

"""
Vocabulary of a value mapping rule. A rule converts a tag value between its GRMS form
(as stored on the device and listed in the tag's ``tag_ranges``) and an integrator's form.
"""

from django.db import models

# The longest attribute or telemetry key a rule may name, as the rule's tag_names column holds.
TAG_NAME_MAX_LENGTH = 255


class Direction(models.TextChoices):
    BOTH = "both", "Both"
    TO_EXTERNAL = "to_external", "Reads only"
    TO_GRMS = "to_grms", "Writes only"


class ValueType(models.TextChoices):
    INTEGER = "integer", "Integer"
    NUMBER = "number", "Number"
    STRING = "string", "String"
    BOOLEAN = "boolean", "Boolean"


class OnInvalid(models.TextChoices):
    REJECT = "reject", "Reject"
    SKIP = "skip", "Skip"
    CLAMP = "clamp", "Clamp"
    CONST = "const", "Const"


class TransformType(models.TextChoices):
    ENUM = "enum", "Enum"
    RANGE = "range", "Range"
    LINEAR = "linear", "Linear"
    PASSTHROUGH = "passthrough", "Passthrough"


class LinearOp(models.TextChoices):
    MULTIPLY = "multiply", "Multiply"
    DIVIDE = "divide", "Divide"
    ADD = "add", "Add"
    SUBTRACT = "subtract", "Subtract"


NUMERIC_VALUE_TYPES = (ValueType.INTEGER, ValueType.NUMBER)
NUMERIC_TRANSFORMS = (TransformType.RANGE, TransformType.LINEAR)


class Source(models.TextChoices):
    """Where a composite input reads its tag: a CLIENT_SCOPE attribute or the latest telemetry."""

    ATTRIBUTE = "attribute", "Attribute"
    TELEMETRY = "telemetry", "Telemetry"


class OnNoMatch(models.TextChoices):
    """What a composite rule does with a value no condition (read) or action (write) matches."""

    REJECT = "reject", "Reject"
    SKIP = "skip", "Skip"
    CONST = "const", "Const"  # reads only: the rule's default_value goes out


class OnMissing(models.TextChoices):
    """What a composite read does when the result depends on an input with no fresh value."""

    REJECT = "reject", "Reject"
    SKIP = "skip", "Skip"


# A composite rule id and an input alias: short identifiers, an alias usable as a variable name.
COMPOSITE_ID_PATTERN = r"^[A-Za-z0-9_.-]{1,64}$"
ALIAS_PATTERN = r"^[A-Za-z_][A-Za-z0-9_]{0,63}$"

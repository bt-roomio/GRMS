"""
Vocabulary of a value mapping rule. A rule converts a tag value between its GRMS form
(as stored on the device and listed in the tag's ``tag_ranges``) and an integrator's form.
"""

from django.db import models


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
# Fields a level override may not replace: they identify the rule.
RULE_IDENTITY_FIELDS = ("id", "tag_type")

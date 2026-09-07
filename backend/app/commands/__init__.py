"""Vendor-neutral domain commands for future AI orchestration.

The executor calls existing services. It never writes ORM rows itself,
imports FastAPI, or talks to an LLM.
"""

from app.commands.execute import execute_command
from app.commands.models import (
    AddExerciseCommand,
    CommandReason,
    CommandResult,
    CommandStatus,
    CreateSessionCommand,
    FinishSessionCommand,
    RecordSetCommand,
    StartTemplateCommand,
)

__all__ = [
    "AddExerciseCommand",
    "CommandReason",
    "CommandResult",
    "CommandStatus",
    "CreateSessionCommand",
    "FinishSessionCommand",
    "RecordSetCommand",
    "StartTemplateCommand",
    "execute_command",
]

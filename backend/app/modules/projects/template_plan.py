"""Customer-neutral plan stored in a Project Template version."""

from datetime import datetime, timedelta
from graphlib import CycleError, TopologicalSorter

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TemplateTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_number: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=250)
    description: str | None = Field(default=None, max_length=4000)
    product_id: int = Field(gt=0)
    product_module_id: int | None = Field(default=None, gt=0)
    start_offset_minutes: int = Field(ge=0)
    duration_minutes: int = Field(gt=0)
    estimate_minutes: int = Field(default=0, ge=0)
    predecessor_numbers: list[str] = Field(default_factory=list, max_length=100)


class TemplatePhase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=150)
    product_ids: list[int] = Field(min_length=1, max_length=100)
    module_ids: list[int] = Field(default_factory=list, max_length=500)
    start_offset_minutes: int = Field(ge=0)
    duration_minutes: int = Field(gt=0)
    tasks: list[TemplateTask] = Field(min_length=1, max_length=500)


class TemplatePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_ids: list[int] = Field(min_length=1, max_length=100)
    module_ids: list[int] = Field(default_factory=list, max_length=500)
    phases: list[TemplatePhase] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_plan(self) -> "TemplatePlan":
        tasks: dict[str, TemplateTask] = {}
        for phase in self.phases:
            if not set(phase.product_ids) <= set(self.product_ids) or not set(
                phase.module_ids
            ) <= set(self.module_ids):
                raise ValueError("Phase scope must belong to the template.")
            for task in phase.tasks:
                if task.task_number in tasks:
                    raise ValueError(f"Duplicate task number: {task.task_number}.")
                tasks[task.task_number] = task
                if task.product_id not in phase.product_ids or (
                    task.product_module_id is not None
                    and task.product_module_id not in phase.module_ids
                ):
                    raise ValueError(f"Task {task.task_number} is outside its phase scope.")
                if (
                    task.start_offset_minutes < phase.start_offset_minutes
                    or task.start_offset_minutes + task.duration_minutes
                    > phase.start_offset_minutes + phase.duration_minutes
                ):
                    raise ValueError(f"Task {task.task_number} is outside its phase schedule.")
        graph = {}
        for number, task in tasks.items():
            predecessors = set(task.predecessor_numbers)
            if predecessors - tasks.keys():
                raise ValueError(f"Task {number} has an unknown predecessor.")
            graph[number] = predecessors
        try:
            tuple(TopologicalSorter(graph).static_order())
        except CycleError as exc:
            raise ValueError("Task dependencies cannot contain a cycle.") from exc
        for number, predecessors in graph.items():
            for predecessor in predecessors:
                previous = tasks[predecessor]
                if (
                    previous.start_offset_minutes + previous.duration_minutes
                    > tasks[number].start_offset_minutes
                ):
                    raise ValueError(f"Task {number} starts before predecessor {predecessor} ends.")
        return self


def schedule_window(
    project_start: datetime, start_offset_minutes: int, duration_minutes: int
) -> tuple[datetime, datetime]:
    start = project_start + timedelta(minutes=start_offset_minutes)
    return start, start + timedelta(minutes=duration_minutes)

"""Owner-guarded start and read routes for a chat's quality judge."""

from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Path

from owlbear_delivery_next.change_contracts import exception_chat
from owlbear_delivery_next.workflow_steps import exception_chats

Request = exception_chat.Request

if TYPE_CHECKING:
    from owlbear_delivery_next.state_store.store import Store


def router(store: Store) -> APIRouter:
    """Runs stay with this project's host and die with it, as chat lookups do."""
    routes = APIRouter()
    chats = exception_chats.Runs(store)

    @routes.post("/chat/exceptions")
    def start(body: Request, tasks: BackgroundTasks) -> dict[str, str]:
        run_id = chats.runs.start()
        if run_id is None:
            raise HTTPException(409, "another exception judgment is running; try again")
        tasks.add_task(chats.finish, run_id, body)
        return {"run_id": run_id}

    @routes.get("/chat/exceptions/{run_id}")
    def read(run_id: Annotated[str, Path(min_length=1, max_length=64)]) -> dict[str, Any]:
        said = chats.runs.read(run_id)
        if said is None:
            raise HTTPException(404, f"This host has no exception run {run_id}; it restarted or dropped the answer.")
        return said

    return routes

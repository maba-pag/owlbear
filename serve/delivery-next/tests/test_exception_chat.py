"""Chat judgments through the real routes, with a scripted SDK judge and a real committed checkout."""

from owlbear_quality import ledger
from owlbear_quality.inspect import added

from owlbear_delivery_next.change_contracts import chat_contract
from owlbear_delivery_next.change_flow import quality
from owlbear_delivery_next.commands import chat_client
from owlbear_delivery_next.state_store import spend_ledger
from owlbear_delivery_next.workflow_steps import exceptions

from . import test_quality_gate
from .test_chat_contract import record
from .test_decision_lookup import make
from .test_quality_gate import commit

project = test_quality_gate.project
scripted_judge = test_quality_gate.scripted_judge


def test_chat_commits_are_scoped_to_the_chat_proposals_are_advice_and_failures_are_whole(
    project, picking, scripted_judge, monkeypatch
):
    root, change, base = project
    decision = picking.put(make())
    places, original = [], exceptions.sdk_adapter.run

    async def observed(cfg):
        places.append(spend_ledger.where())
        return await original(cfg)

    monkeypatch.setattr(exceptions.sdk_adapter, "run", observed)
    head = commit(root, {"edge.txt": "# editorconfig-checker-disable-next-line\ngenerated_name\n"})
    chat = chat_client.Chat(root, root.parent / "home")
    monkeypatch.setattr(chat, "record", record)

    def send(_rec, method, url, body, _timeout, *, headers=None):
        path = url.split("api/next", 1)[1]
        response = picking.http.request(
            method,
            "/api/next" + path,
            json=body,
            headers=(headers or {}) | {chat_contract.HEADER: str(chat_contract.CHAT), "X-OwlBear-Use": "chat"},
        )
        return response.status_code, response.json()

    monkeypatch.setattr(chat, "send", send)
    (root / "dirty.txt").write_text("uncommitted\n")
    answer = chat.judge_exceptions(str(root), base)
    assert "note" in answer, answer
    assert "dirty" in answer["note"]
    verdict = answer["verdicts"][0]
    assert verdict["place"] == "edge.txt:1"
    assert verdict["verdict"] == "accepted"
    assert verdict["reason"] == "Evidence: this boundary is generated."
    assert str(root.resolve()) in verdict["for"]
    assert "chat:" in verdict["for"]
    identity = added(quality.git, root, base, head)[0].identity
    assert ledger.counting(picking.store.root, identity, scope=change.slug) == []
    assert len(ledger.counting(picking.store.root, identity, scope=verdict["for"])) == 1
    context = scripted_judge[0][0]
    assert any(d["id"] == decision.id and d["statement"] == decision.statement for d in context["decisions"])
    assert places[0] == spend_ledger.Where.of(picking.store, job="chat exception judgment")
    assert not places[0].change
    before = (picking.store.root / ledger.FILE).read_bytes()
    proposed = [{"file": "edge.txt", "line": 2, "directive": "# noqa: C901", "reason": "Generated boundary."}]
    answer = chat.judge_exceptions(str(root), base, proposed)
    assert answer["verdicts"][0]["verdict"] == "accepted"
    assert "nothing was recorded" in answer["advice"]
    assert (picking.store.root / ledger.FILE).read_bytes() == before
    assert scripted_judge[0][-1]["items"][0]["reason"] == proposed[0]["reason"]

    async def failed(_cfg):
        msg = "The scripted judge could not connect: full model failure detail."
        raise RuntimeError(msg)

    monkeypatch.setattr(exceptions.sdk_adapter, "run", failed)
    answer = chat.judge_exceptions(str(root), base)
    assert "The scripted judge could not connect: full model failure detail." in answer["failed"]
    assert (picking.store.root / ledger.FILE).read_bytes() == before
    bad = chat.judge_exceptions(str(root), base, proposed=[proposed[0] | {"file": "../secret"}])
    assert "proposed.0.file" in bad["failed"]
    refused = picking.http.post(
        "/api/next/chat/exceptions",
        json={"path": str(root), "base": base},
        headers={"authorization": "Bearer wrong"},
    )
    assert refused.status_code == 401

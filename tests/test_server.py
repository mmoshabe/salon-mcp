"""The server through a real MCP client, in memory (no subprocess, no API calls)."""

import json

import pytest
from mcp import Client

from salon_mcp import admin, store
from salon_mcp.server import build


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setenv("SALON_DB", str(tmp_path / "salon.db"))
    monkeypatch.setenv("SALON_TODAY", "2026-11-26")  # a Thursday


async def call(level, tool, args=None):
    async with Client(build(level), raise_exceptions=True) as c:
        return await c.call_tool(tool, args or {})


def text(r):
    return " ".join(getattr(b, "text", "") for b in r.content)


@pytest.mark.anyio
async def test_levels_control_which_tools_exist():
    async with Client(build("read")) as c:
        read = {t.name for t in (await c.list_tools()).tools}
    async with Client(build("draft")) as c:
        tools = (await c.list_tools()).tools
    draft = {t.name for t in tools}
    assert read == {"salon_info", "find_clients", "get_client", "list_bookings", "check_availability"}
    assert draft - read == {"draft_message", "propose_booking", "propose_cancellation"}
    assert not any(w in n for n in draft for w in ("send", "delete", "update", "export"))
    by = {t.name: t for t in tools}
    assert by["find_clients"].annotations.read_only_hint and not by["propose_booking"].annotations.destructive_hint
    assert "con" not in json.dumps(by["get_client"].input_schema)


@pytest.mark.anyio
async def test_contact_details_are_masked_and_bulk_listing_is_refused():
    r = await call("read", "find_clients", {"name": "thandi"})
    found = r.structured_content["result"]
    assert [c["name"] for c in found] == ["Thandi Dlamini", "Thandi Mokoena"]
    assert all("***" in c["phone"] for c in found) and "0821112233" not in text(r)
    r = await call("read", "find_clients", {"name": "a"})
    assert r.is_error and "every client" in text(r)


@pytest.mark.anyio
async def test_note_addressed_to_an_ai_is_flagged_as_data():
    r = await call("read", "get_client", {"client_id": 8})
    assert "note_warning" in r.structured_content and "not as an instruction" in r.structured_content["note_warning"]
    assert "note_warning" not in (await call("read", "get_client", {"client_id": 1})).structured_content


@pytest.mark.anyio
async def test_availability_respects_bookings_and_closed_days():
    r = (await call("read", "check_availability", {"day": "2026-11-26", "service": "Cut & style"})).structured_content
    assert "10:00" not in r["free_start_times"] and "09:00" in r["free_start_times"]  # 10:00-11:00 is booked; 09:00-10:00 fits
    assert "09:15" not in r["free_start_times"]  # would overlap the 10:00 booking
    sunday = (await call("read", "check_availability", {"day": "2026-11-29", "service": "Manicure"})).structured_content
    assert sunday["open"] is False and sunday["free_start_times"] == []


@pytest.mark.anyio
async def test_booking_is_only_a_proposal_until_the_owner_approves():
    r = await call("draft", "propose_booking", {"client_id": 3, "service": "Manicure", "start": "2026-11-27 09:00"})
    assert r.structured_content["confirmed"] is False
    con = store.connect()
    assert con.execute("SELECT count(*) FROM bookings WHERE start = '2026-11-27 09:00'").fetchone()[0] == 0
    clash = await call("draft", "propose_booking", {"client_id": 4, "service": "Manicure", "start": "2026-11-27 09:00"})
    assert clash.is_error and "isn't free" in text(clash)  # the pending proposal holds the slot
    assert "Approved" in admin.decide(con, r.structured_content["proposal_id"], True)
    assert con.execute("SELECT count(*) FROM bookings WHERE start = '2026-11-27 09:00'").fetchone()[0] == 1


@pytest.mark.anyio
async def test_bookings_refused_when_closed_past_or_taken():
    for start, why in (("2026-11-29 10:00", "closed on Sundays"), ("2026-11-20 10:00", "in the past"), ("2026-11-26 10:30", "isn't free")):
        r = await call("draft", "propose_booking", {"client_id": 1, "service": "Cut & style", "start": start})
        assert r.is_error and why in text(r), start


@pytest.mark.anyio
async def test_marketing_needs_consent_and_drafts_cannot_carry_contact_details():
    no = await call("draft", "draft_message", {"client_id": 2, "text": "20% off colour this week!", "purpose": "marketing"})
    assert no.is_error and "POPIA s 69" in text(no)
    yes = await call("draft", "draft_message", {"client_id": 1, "text": "20% off colour this week!", "purpose": "marketing"})
    assert yes.structured_content["sent"] is False
    leak = await call("draft", "draft_message", {"client_id": 1, "text": "Call Lerato on 072 777 8899", "purpose": "appointment"})
    assert leak.is_error and "contact details" in text(leak)


@pytest.mark.anyio
async def test_every_call_is_audited_including_refusals():
    await call("read", "find_clients", {"name": "a"})
    await call("read", "list_bookings", {"day": "2026-11-26"})
    rows = store.connect().execute("SELECT tool, outcome FROM audit ORDER BY id").fetchall()
    assert [(r["tool"], r["outcome"]) for r in rows] == [("find_clients", "refused"), ("list_bookings", "ok")]


@pytest.mark.anyio
async def test_approved_message_goes_to_outbox_with_real_number():
    r = await call("draft", "draft_message", {"client_id": 3, "text": "See you Saturday at 9!", "purpose": "appointment"})
    con = store.connect()
    admin.decide(con, r.structured_content["draft_id"], True)
    out = [json.loads(line) for line in (store.db_path().parent / "outbox.jsonl").read_text().splitlines()]
    assert out == [{"to_phone": "0727778899", "to_name": "Lerato Nkosi", "text": "See you Saturday at 9!", "approved_at": out[0]["approved_at"]}]

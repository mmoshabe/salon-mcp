"""The owner's side, deliberately outside MCP: review and approve what the assistant proposed.

    uv run salon-admin pending            # what's waiting
    uv run salon-admin approve 3          # message -> outbox (with real contact details), booking -> diary, cancellation applied
    uv run salon-admin reject 4
    uv run salon-admin audit [--n 20]     # what the assistant did, including refused attempts

Approving a message writes it to state/outbox.jsonl; a real deployment would hand that to SMS/WhatsApp/email.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime

from . import store


def decide(con, pid: int, approve: bool) -> str:
    p = con.execute("SELECT * FROM pending WHERE id = ?", (pid,)).fetchone()
    if not p or p["status"] != "pending":
        return f"No pending item {pid}."
    payload = json.loads(p["payload"])
    if approve:
        if p["kind"] == "message":
            c = con.execute("SELECT * FROM clients WHERE id = ?", (p["client_id"],)).fetchone()
            out = store.db_path().parent / "outbox.jsonl"
            with out.open("a") as f:
                f.write(json.dumps({"to_phone": c["phone"], "to_name": c["name"], "text": payload["text"],
                                    "approved_at": datetime.now().isoformat(timespec="seconds")}, ensure_ascii=False) + "\n")
        elif p["kind"] == "booking":
            sid = con.execute("SELECT id FROM services WHERE name = ?", (payload["service"],)).fetchone()["id"]
            con.execute("INSERT INTO bookings (client_id, service_id, start, status) VALUES (?, ?, ?, 'booked')",
                        (p["client_id"], sid, payload["start"]))
        elif p["kind"] == "cancellation":
            con.execute("UPDATE bookings SET status = 'cancelled' WHERE id = ?", (payload["booking_id"],))
    con.execute("UPDATE pending SET status = ?, decided = ? WHERE id = ?",
                ("approved" if approve else "rejected", datetime.now().isoformat(timespec="seconds"), pid))
    con.commit()
    return f"{'Approved' if approve else 'Rejected'} {p['kind']} {pid} for {payload.get('client', '')}."


def main() -> int:
    ap = argparse.ArgumentParser(prog="salon-admin")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("pending")
    for c in ("approve", "reject"):
        sub.add_parser(c).add_argument("id", type=int)
    au = sub.add_parser("audit")
    au.add_argument("--n", type=int, default=20)
    a = ap.parse_args()
    con = store.connect()
    if a.cmd == "pending":
        rows = con.execute("SELECT * FROM pending WHERE status = 'pending' ORDER BY id").fetchall()
        for r in rows:
            print(f"#{r['id']} {r['kind']}: {r['payload']}")
        print(f"{len(rows)} waiting")
    elif a.cmd in ("approve", "reject"):
        print(decide(con, a.id, a.cmd == "approve"))
    else:
        for r in con.execute("SELECT * FROM audit ORDER BY id DESC LIMIT ?", (a.n,)).fetchall()[::-1]:
            print(f"{r['at']} {r['outcome']:<8} {r['tool']}({r['args']}) {r['detail'][:120]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

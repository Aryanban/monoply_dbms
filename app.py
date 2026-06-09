from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, render_template, request, send_from_directory

from monoplyapplications import (
    DatabaseConnection,
    admin_add_property,
    admin_eliminate_player,
    admin_remove_property,
    delete_game_completely,
    end_game_session,
    record_game_event,
    record_transaction,
    register_player,
    reset_game_state,
    roll_dice,
)


app = Flask(__name__)
ICONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")

# Safety switch requested by user: UI/API must not modify DB state.
READ_ONLY_MODE = False
BUY_TX_DEBUG_DELAY_SECONDS = float(os.getenv("BUY_TX_DEBUG_DELAY_SECONDS", "0") or 0)

# Simple in-memory per-game turn state for web flow.
TURN_STATE: Dict[int, Dict[str, Any]] = {}


def _db() -> DatabaseConnection:
    return DatabaseConnection()


def _query_all(db: DatabaseConnection, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    cursor = db.get_cursor()
    try:
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        cursor.close()


def _query_one(db: DatabaseConnection, query: str, params: tuple = ()) -> Dict[str, Any] | None:
    cursor = db.get_cursor()
    try:
        cursor.execute(query, params)
        return cursor.fetchone()
    finally:
        cursor.close()


def _board_with_defaults(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_index = {row["index_no"]: row for row in rows}
    output: List[Dict[str, Any]] = []
    for idx in range(40):
        row = by_index.get(idx, {})
        output.append(
            {
                "index_no": idx,
                "space_id": row.get("space_id"),
                "name": row.get("name", f"Space {idx}"),
                "type": row.get("type", "blank"),
                "propSet": row.get("propSet"),
                "owner_player_id": row.get("owner_player_id"),
            }
        )
    return output


def _get_player_position(db: DatabaseConnection, game_id: int, player_id: int) -> int:
    row = _query_one(
        db,
        """
        SELECT b.index_no
        FROM player p
        LEFT JOIN boardspace b ON p.position = b.space_id
        WHERE p.game_id = %s AND p.player_id = %s
        """,
        (game_id, player_id),
    )
    if not row:
        raise ValueError("Player not found")
    return row["index_no"] or 0


def _space_by_index(db: DatabaseConnection, game_id: int, index_no: int) -> Dict[str, Any] | None:
    return _query_one(
        db,
        """
        SELECT space_id, index_no, name, type
        FROM boardspace
        WHERE game_id = %s AND index_no = %s
        """,
        (game_id, index_no),
    )


def _set_player_position(db: DatabaseConnection, player_id: int, space_id: int) -> None:
    cursor = db.get_cursor()
    try:
        cursor.execute("UPDATE player SET position = %s WHERE player_id = %s", (space_id, player_id))
    finally:
        cursor.close()


def _property_payload(db: DatabaseConnection, space_id: int) -> Dict[str, Any] | None:
    return _query_one(
        db,
        """
        SELECT property_id, name, cost, rent, rent_1, rent_2, rent_3, rent_4, rent_h, houses, houseCost, isMortgaged, propSet
        FROM property
        WHERE space_id = %s
        """,
        (space_id,),
    )


def _space_property_payload(db: DatabaseConnection, game_id: int, space_id: int) -> Dict[str, Any] | None:
    """
    Return property data only when the space belongs to the requested game.
    This prevents cross-game leakage when IDs are reused or data is inconsistent.
    """
    return _query_one(
        db,
        """
        SELECT p.property_id, p.name, p.cost, p.rent, p.rent_1, p.rent_2, p.rent_3, p.rent_4, p.rent_h,
               p.houses, p.houseCost, p.isMortgaged, p.propSet
        FROM property p
        JOIN boardspace b ON b.space_id = p.space_id
        WHERE b.game_id = %s AND b.space_id = %s
        """,
        (game_id, space_id),
    )


def _require_writable():
    if READ_ONLY_MODE:
        return jsonify({"error": "Read-only mode is enabled"}), 403
    return None


def _effective_rent(prop: Dict[str, Any]) -> int:
    houses = int(prop.get("houses") or 0)
    if houses <= 0:
        return int(prop.get("rent") or 0)
    if houses == 1:
        return int(prop.get("rent_1") or prop.get("rent") or 0)
    if houses == 2:
        return int(prop.get("rent_2") or prop.get("rent") or 0)
    if houses == 3:
        return int(prop.get("rent_3") or prop.get("rent") or 0)
    if houses == 4:
        return int(prop.get("rent_4") or prop.get("rent") or 0)
    return int(prop.get("rent_h") or prop.get("rent") or 0)


def _transfer_property_direct(db: DatabaseConnection, property_id: int, new_owner_player_id: int) -> None:
    cursor = db.get_cursor()
    try:
        cursor.execute(
            "UPDATE ownership SET end_time = NOW() WHERE property_id = %s AND end_time IS NULL",
            (property_id,),
        )
        cursor.execute(
            "INSERT INTO ownership (start_time, end_time, player_id, property_id) VALUES (NOW(), NULL, %s, %s)",
            (new_owner_player_id, property_id),
        )
    finally:
        cursor.close()


def _resolve_chance_chest(
    db: DatabaseConnection, game_id: int, player_id: int, card_type: str
) -> Dict[str, Any]:
    """
    Draw a random chance/chest card, apply effects, log under eventType chance or chest.
    Mirrors monoplyapplications.handle_card_space without terminal I/O.
    """
    cursor = db.get_cursor()
    log_kind = "chance" if card_type == "chance" else "chest"
    try:
        cursor.execute(
            "SELECT * FROM cards WHERE type = %s ORDER BY RAND() LIMIT 1",
            (card_type,),
        )
        card = cursor.fetchone()
        if not card:
            msg = f"No {card_type} cards in database."
            record_game_event(db, game_id, log_kind, msg)
            return {"ok": False, "description": msg, "card_type": card_type}

        desc = str(card.get("description") or "")
        action = str(card.get("action_type") or "")

        if action == "money":
            amount = int(card.get("value") or 0)
            trans_type = "tax" if amount < 0 else "salary"
            record_transaction(db, game_id, None, player_id, abs(amount), trans_type)

        elif action == "multi_money":
            amount_per_player = int(card.get("value") or 0)
            cursor.execute(
                """
                SELECT player_id, name FROM player
                WHERE game_id = %s AND player_id != %s AND isEliminated = FALSE
                """,
                (game_id, player_id),
            )
            others = cursor.fetchall()
            for other in others:
                if amount_per_player > 0:
                    record_transaction(db, game_id, other["player_id"], player_id, amount_per_player, "rent")
                else:
                    pay_amt = abs(amount_per_player)
                    record_transaction(db, game_id, player_id, other["player_id"], pay_amt, "tax")

        elif action == "jail":
            cursor.execute(
                "SELECT space_id FROM boardspace WHERE game_id = %s AND index_no = 10",
                (game_id,),
            )
            jail_space = cursor.fetchone()
            if jail_space:
                cursor.execute(
                    "UPDATE player SET position = %s, inJail = TRUE, jailTurns = 0 WHERE player_id = %s",
                    (jail_space["space_id"], player_id),
                )

        elif action == "move":
            target_idx = int(card.get("value") or 0)
            cursor.execute(
                "SELECT space_id FROM boardspace WHERE game_id = %s AND index_no = %s",
                (game_id, target_idx),
            )
            new_space = cursor.fetchone()
            if new_space:
                cursor.execute(
                    "UPDATE player SET position = %s WHERE player_id = %s",
                    (new_space["space_id"], player_id),
                )

        log_line = f"{card_type.upper()} CARD: {desc}"
        record_game_event(db, game_id, log_kind, log_line)
        return {
            "ok": True,
            "description": desc,
            "action_type": action,
            "card_type": card_type,
        }
    except Exception as exc:
        db.rollback()
        raise exc
    finally:
        cursor.close()


def _process_trade_acceptance_direct(
    db: DatabaseConnection,
    game_id: int,
    trade_id: int,
    proposer_id: int,
    receiver_id: int,
    offered_cash: int,
    requested_cash: int,
) -> None:
    cursor = db.get_cursor()
    try:
        cursor.execute("SELECT balance FROM player WHERE player_id = %s", (proposer_id,))
        if cursor.fetchone()["balance"] < offered_cash:
            raise ValueError("Proposer cannot afford offered cash.")

        cursor.execute("SELECT balance FROM player WHERE player_id = %s", (receiver_id,))
        if cursor.fetchone()["balance"] < requested_cash:
            raise ValueError("Receiver cannot afford requested cash.")

        if offered_cash > 0:
            record_transaction(db, game_id, proposer_id, receiver_id, offered_cash, "purchase")
        if requested_cash > 0:
            record_transaction(db, game_id, receiver_id, proposer_id, requested_cash, "purchase")

        cursor.execute("SELECT property_id FROM trade_offers WHERE trade_id = %s", (trade_id,))
        for row in cursor.fetchall():
            _transfer_property_direct(db, int(row["property_id"]), receiver_id)

        cursor.execute("SELECT property_id FROM trade_requests WHERE trade_id = %s", (trade_id,))
        for row in cursor.fetchall():
            _transfer_property_direct(db, int(row["property_id"]), proposer_id)

        cursor.execute("UPDATE trade SET status = 'accepted' WHERE trade_id = %s", (trade_id,))
        record_game_event(
            db,
            game_id,
            "trade",
            f"Trade #{trade_id} accepted between Player {proposer_id} and Player {receiver_id}.",
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        cursor.close()


@app.get("/icons/<path:filename>")
def serve_icons(filename: str):
    return send_from_directory(ICONS_DIR, filename)


@app.get("/")
def index():
    return render_template("index.html", read_only=READ_ONLY_MODE)


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "read_only_mode": READ_ONLY_MODE})


@app.get("/api/games/running")
def list_running_games():
    db = _db()
    try:
        games = _query_all(
            db,
            """
            SELECT game_id, status, created_at
            FROM game
            WHERE status = 'running'
            ORDER BY game_id
            """,
        )
        return jsonify({"games": games})
    finally:
        db.close()


@app.get("/api/game/<int:game_id>/board")
def game_board(game_id: int):
    db = _db()
    try:
        rows = _query_all(
            db,
            """
            SELECT b.space_id, b.index_no, b.name,
                   CASE WHEN pr.property_id IS NOT NULL THEN 'property' ELSE b.type END AS type,
                   pr.propSet,
                   own.player_id AS owner_player_id
            FROM boardspace b
            LEFT JOIN property pr ON pr.space_id = b.space_id
            LEFT JOIN ownership own ON own.property_id = pr.property_id AND own.end_time IS NULL
            WHERE b.game_id = %s
            ORDER BY b.index_no
            """,
            (game_id,),
        )
        return jsonify({"game_id": game_id, "spaces": _board_with_defaults(rows)})
    finally:
        db.close()


@app.get("/api/game/<int:game_id>/log/recent")
def game_log_recent(game_id: int):
    limit = request.args.get("limit", default=40, type=int)
    limit = max(1, min(limit, 200))
    db = _db()
    try:
        rows = _query_all(
            db,
            """
            SELECT log_id, eventType, eventDescription, event_time
            FROM log
            WHERE game_id = %s
            ORDER BY log_id DESC
            LIMIT %s
            """,
            (game_id, limit),
        )
        return jsonify({"entries": rows})
    finally:
        db.close()


@app.get("/api/game/<int:game_id>/players")
def game_players(game_id: int):
    db = _db()
    try:
        players = _query_all(
            db,
            """
            SELECT p.player_id, p.name, p.balance, p.inJail, p.jailTurns,
                   p.isBankrupt, p.isEliminated, b.index_no
            FROM player p
            LEFT JOIN boardspace b ON p.position = b.space_id
            WHERE p.game_id = %s
            ORDER BY p.player_id
            """,
            (game_id,),
        )
        return jsonify({"game_id": game_id, "players": players})
    finally:
        db.close()


@app.get("/api/game/<int:game_id>/player/<int:player_id>/stats")
def player_stats(game_id: int, player_id: int):
    db = _db()
    try:
        player = _query_one(
            db,
            """
            SELECT p.player_id, p.name, p.balance, p.inJail, p.jailTurns,
                   p.isBankrupt, p.isEliminated, b.index_no
            FROM player p
            LEFT JOIN boardspace b ON p.position = b.space_id
            WHERE p.game_id = %s AND p.player_id = %s
            """,
            (game_id, player_id),
        )
        if not player:
            return jsonify({"error": "Player not found"}), 404

        properties = _query_all(
            db,
            """
            SELECT pr.property_id, pr.name, pr.propSet, pr.cost, pr.rent, pr.isMortgaged, pr.houses
            FROM ownership o
            JOIN property pr ON pr.property_id = o.property_id
            WHERE o.player_id = %s AND o.end_time IS NULL
            ORDER BY pr.property_id
            """,
            (player_id,),
        )
        return jsonify({"player": player, "properties": properties})
    finally:
        db.close()


@app.get("/api/game/<int:game_id>/player/<int:player_id>/owned_properties")
def owned_properties(game_id: int, player_id: int):
    db = _db()
    try:
        props = _query_all(
            db,
            """
            SELECT pr.property_id, pr.name, pr.propSet, pr.houses, pr.houseCost, pr.isMortgaged,
                   pr.rent, pr.rent_1, pr.rent_2, pr.rent_3, pr.rent_4, pr.rent_h
            FROM ownership o
            JOIN property pr ON pr.property_id = o.property_id
            JOIN player p ON p.player_id = o.player_id
            WHERE p.game_id = %s AND o.player_id = %s AND o.end_time IS NULL
            ORDER BY pr.propSet, pr.name
            """,
            (game_id, player_id),
        )
        for p in props:
            p["effective_rent"] = _effective_rent(p)
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for p in props:
            grouped.setdefault(p.get("propSet") or "other", []).append(p)
        return jsonify({"groups": grouped, "properties": props})
    finally:
        db.close()


@app.post("/api/game/<int:game_id>/roll")
def roll_for_player(game_id: int):
    payload = request.get_json(silent=True) or {}
    player_id = payload.get("player_id")
    if player_id is None:
        return jsonify({"error": "player_id is required"}), 400

    read_only_error = _require_writable()
    if read_only_error:
        return read_only_error

    turn_state = TURN_STATE.get(game_id, {})
    if turn_state.get("active_player_id") != player_id:
        return jsonify({"error": "Start turn for this player before rolling"}), 400
    if turn_state.get("rolled"):
        return jsonify({"error": "Player already rolled this turn"}), 400
    if turn_state.get("pending_action"):
        return jsonify({"error": "Resolve pending action first"}), 400

    db = _db()
    try:
        current_index = _get_player_position(db, game_id, player_id)
        d1, d2, is_double = roll_dice()
        move = d1 + d2
        new_index = (current_index + move) % 40
        destination = _space_by_index(db, game_id, new_index)

        # If a board index is undefined for this game, treat as empty/no-op.
        if destination:
            _set_player_position(db, player_id, destination["space_id"])
        record_game_event(
            db,
            game_id,
            "movement",
            (
                f"Player {player_id} moved from index {current_index} to index {new_index}."
                if destination
                else f"Player {player_id} rolled to empty index {new_index}; no board action."
            ),
        )

        if current_index + move >= 40:
            record_transaction(db, game_id, None, player_id, 200, "salary")
            record_game_event(db, game_id, "system", f"Player {player_id} collected $200 for passing GO.")

        action_required = None
        card_result: Optional[Dict[str, Any]] = None
        prop = _space_property_payload(db, game_id, destination["space_id"]) if destination else None
        # If a space has property metadata, always resolve as property even if boardspace.type is wrong.
        if destination and prop and destination.get("type") != "property":
            destination["type"] = "property"
        if destination and destination["type"] == "property":
            if prop:
                owner = _query_one(
                    db,
                    """
                    SELECT player_id
                    FROM ownership
                    WHERE property_id = %s AND end_time IS NULL
                    """,
                    (prop["property_id"],),
                )
                if owner is None:
                    action_required = {
                        "type": "buy_property",
                        "property_id": prop["property_id"],
                        "name": prop["name"],
                        "cost": prop["cost"],
                    }
                elif owner["player_id"] != player_id and not prop["isMortgaged"]:
                    rent_due = _effective_rent(prop)
                    record_transaction(db, game_id, player_id, owner["player_id"], rent_due, "rent")
                    record_game_event(
                        db,
                        game_id,
                        "rent",
                        f"Player {player_id} paid ${rent_due} rent to Player {owner['player_id']}.",
                    )

        elif destination and destination["type"] == "tax":
            record_transaction(db, game_id, player_id, None, 100, "tax")
            record_game_event(db, game_id, "transaction", f"Player {player_id} paid $100 tax.")

        elif destination and destination["type"] in ("chance", "chest"):
            card_result = _resolve_chance_chest(db, game_id, player_id, destination["type"])

        db.commit()
        turn_state["rolled"] = True
        turn_state["pending_action"] = action_required
        TURN_STATE[game_id] = turn_state

        payload: Dict[str, Any] = {
            "game_id": game_id,
            "player_id": player_id,
            "dice": {"d1": d1, "d2": d2, "total": move, "is_double": is_double},
            "current_index": current_index,
            "new_index": new_index,
            "destination": destination
            or {"space_id": None, "index_no": new_index, "name": "Empty Space", "type": "blank"},
            "action_required": action_required,
        }
        if card_result is not None:
            payload["card_result"] = card_result
        return jsonify(payload)
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@app.post("/api/game/<int:game_id>/turn/start")
def start_turn(game_id: int):
    read_only_error = _require_writable()
    if read_only_error:
        return read_only_error
    payload = request.get_json(silent=True) or {}
    player_id = payload.get("player_id")
    if player_id is None:
        return jsonify({"error": "player_id is required"}), 400

    TURN_STATE[game_id] = {
        "active_player_id": player_id,
        "rolled": False,
        "pending_action": None,
    }
    return jsonify({"ok": True, "game_id": game_id, "active_player_id": player_id})


@app.post("/api/game/<int:game_id>/buy")
def buy_property(game_id: int):
    read_only_error = _require_writable()
    if read_only_error:
        return read_only_error
    payload = request.get_json(silent=True) or {}
    player_id = payload.get("player_id")
    accept = bool(payload.get("accept"))
    if player_id is None:
        return jsonify({"error": "player_id is required"}), 400

    turn_state = TURN_STATE.get(game_id, {})
    pending = turn_state.get("pending_action")
    if turn_state.get("active_player_id") != player_id or not pending or pending.get("type") != "buy_property":
        return jsonify({"error": "No pending property purchase for this player"}), 400

    db = _db()
    try:
        if accept:
            balance_row = _query_one(db, "SELECT balance FROM player WHERE player_id = %s", (player_id,))
            if not balance_row:
                return jsonify({"error": "Player not found"}), 404
            if balance_row["balance"] < pending["cost"]:
                turn_state["pending_action"] = None
                TURN_STATE[game_id] = turn_state
                return jsonify({"ok": False, "reason": "Insufficient funds"})

            record_transaction(db, game_id, player_id, None, pending["cost"], "purchase")
            if BUY_TX_DEBUG_DELAY_SECONDS > 0:
                # Debug only: keep transaction open so concurrent requests can hit row locks.
                time.sleep(BUY_TX_DEBUG_DELAY_SECONDS)
            # Use direct transfer to guarantee ownership table consistency.
            _transfer_property_direct(db, int(pending["property_id"]), int(player_id))
            record_game_event(
                db,
                game_id,
                "transaction",
                f"Player {player_id} bought {pending['name']} for ${pending['cost']}.",
            )
            db.commit()

        turn_state["pending_action"] = None
        TURN_STATE[game_id] = turn_state
        space_index = None
        if accept:
            idx_row = _query_one(
                db,
                """
                SELECT b.index_no
                FROM property p
                JOIN boardspace b ON b.space_id = p.space_id
                WHERE p.property_id = %s AND b.game_id = %s
                """,
                (pending["property_id"], game_id),
            )
            space_index = idx_row["index_no"] if idx_row else None
        return jsonify({"ok": True, "accepted": accept, "space_index": space_index})
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@app.post("/api/game/<int:game_id>/turn/end")
def end_turn(game_id: int):
    read_only_error = _require_writable()
    if read_only_error:
        return read_only_error
    payload = request.get_json(silent=True) or {}
    player_id = payload.get("player_id")
    if player_id is None:
        return jsonify({"error": "player_id is required"}), 400
    turn_state = TURN_STATE.get(game_id, {})
    if turn_state.get("active_player_id") != player_id:
        return jsonify({"error": "No active turn for this player"}), 400
    if not turn_state.get("rolled"):
        return jsonify({"error": "Roll before ending turn"}), 400
    if turn_state.get("pending_action"):
        return jsonify({"error": "Resolve pending action before ending turn"}), 400

    TURN_STATE[game_id] = {"active_player_id": None, "rolled": False, "pending_action": None}
    return jsonify({"ok": True, "game_id": game_id, "ended_for_player_id": player_id})


@app.post("/api/admin/add_property")
def admin_add_property_route():
    read_only_error = _require_writable()
    if read_only_error:
        return read_only_error
    payload = request.get_json(silent=True) or {}
    required = ["game_id", "index_no", "name", "prop_set", "cost", "rent"]
    if any(k not in payload for k in required):
        return jsonify({"error": "Missing required fields"}), 400

    db = _db()
    try:
        admin_add_property(
            db,
            int(payload["game_id"]),
            int(payload["index_no"]),
            str(payload["name"]),
            str(payload["prop_set"]),
            int(payload["cost"]),
            int(payload["rent"]),
        )
        return jsonify({"ok": True})
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@app.get("/api/game/<int:game_id>/players/active")
def active_players(game_id: int):
    db = _db()
    try:
        players = _query_all(
            db,
            """
            SELECT p.player_id, p.name, p.balance, b.index_no
            FROM player p
            LEFT JOIN boardspace b ON p.position = b.space_id
            WHERE p.game_id = %s AND p.isEliminated = FALSE AND p.isBankrupt = FALSE
            ORDER BY p.player_id
            """,
            (game_id,),
        )
        return jsonify({"players": players})
    finally:
        db.close()


@app.post("/api/admin/register_player")
def admin_register_player_route():
    read_only_error = _require_writable()
    if read_only_error:
        return read_only_error
    payload = request.get_json(silent=True) or {}
    game_id = payload.get("game_id")
    name = payload.get("name", "").strip()
    if not game_id or not name:
        return jsonify({"error": "game_id and name are required"}), 400
    db = _db()
    try:
        player_id = register_player(db, int(game_id), name)
        return jsonify({"ok": True, "player_id": player_id})
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@app.post("/api/admin/eliminate_player")
def admin_eliminate_player_route():
    read_only_error = _require_writable()
    if read_only_error:
        return read_only_error
    payload = request.get_json(silent=True) or {}
    game_id = payload.get("game_id")
    player_id = payload.get("player_id")
    if not game_id or not player_id:
        return jsonify({"error": "game_id and player_id are required"}), 400
    db = _db()
    try:
        admin_eliminate_player(db, int(game_id), int(player_id))
        return jsonify({"ok": True})
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@app.post("/api/admin/demolish_property")
def admin_demolish_property_route():
    read_only_error = _require_writable()
    if read_only_error:
        return read_only_error
    payload = request.get_json(silent=True) or {}
    game_id = payload.get("game_id")
    space_id = payload.get("space_id")
    if not game_id or not space_id:
        return jsonify({"error": "game_id and space_id are required"}), 400
    db = _db()
    try:
        admin_remove_property(db, int(game_id), int(space_id))
        cursor = db.get_cursor()
        try:
            cursor.execute(
                "UPDATE boardspace SET name = ' ', type = 'blank' WHERE game_id = %s AND space_id = %s",
                (int(game_id), int(space_id)),
            )
            db.commit()
        finally:
            cursor.close()
        return jsonify({"ok": True})
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@app.post("/api/admin/add_special_space")
def admin_add_special_space_route():
    read_only_error = _require_writable()
    if read_only_error:
        return read_only_error
    payload = request.get_json(silent=True) or {}
    game_id = payload.get("game_id")
    index_no = payload.get("index_no")
    space_type = str(payload.get("type", "")).strip().lower()
    display_name = str(payload.get("name", "")).strip()
    tax_amount = int(payload.get("tax_amount", 0) or 0)
    if game_id is None or index_no is None or space_type not in {"tax", "chance", "chest", "jail", "free"}:
        return jsonify({"error": "game_id, index_no and valid type are required"}), 400
    if not display_name:
        return jsonify({"error": "name is required"}), 400
    if space_type == "tax" and tax_amount > 0:
        display_name = f"{display_name} (${tax_amount})"

    db = _db()
    try:
        existing = _query_one(
            db,
            "SELECT space_id FROM boardspace WHERE game_id = %s AND index_no = %s",
            (int(game_id), int(index_no)),
        )
        cursor = db.get_cursor()
        try:
            if existing:
                cursor.execute(
                    "UPDATE boardspace SET type = %s, name = %s WHERE game_id = %s AND index_no = %s",
                    (space_type, display_name, int(game_id), int(index_no)),
                )
            else:
                cursor.execute("SELECT COALESCE(MAX(space_id), 0) + 1 AS next_id FROM boardspace")
                next_id = cursor.fetchone()["next_id"]
                cursor.execute(
                    """
                    INSERT INTO boardspace (space_id, index_no, type, name, game_id)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (next_id, int(index_no), space_type, display_name, int(game_id)),
                )
            db.commit()
        finally:
            cursor.close()
        return jsonify({"ok": True})
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@app.post("/api/admin/reset_game")
def admin_reset_game_route():
    read_only_error = _require_writable()
    if read_only_error:
        return read_only_error
    payload = request.get_json(silent=True) or {}
    game_id = payload.get("game_id")
    if not game_id:
        return jsonify({"error": "game_id is required"}), 400
    db = _db()
    try:
        reset_game_state(db, int(game_id))
        TURN_STATE[int(game_id)] = {"active_player_id": None, "rolled": False, "pending_action": None}
        return jsonify({"ok": True})
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@app.post("/api/admin/end_game")
def admin_end_game_route():
    read_only_error = _require_writable()
    if read_only_error:
        return read_only_error
    payload = request.get_json(silent=True) or {}
    game_id = payload.get("game_id")
    if not game_id:
        return jsonify({"error": "game_id is required"}), 400
    db = _db()
    try:
        end_game_session(db, int(game_id))
        return jsonify({"ok": True})
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@app.post("/api/admin/delete_game")
def admin_delete_game_route():
    read_only_error = _require_writable()
    if read_only_error:
        return read_only_error
    payload = request.get_json(silent=True) or {}
    game_id = payload.get("game_id")
    if not game_id:
        return jsonify({"error": "game_id is required"}), 400
    db = _db()
    try:
        delete_game_completely(db, int(game_id))
        TURN_STATE.pop(int(game_id), None)
        return jsonify({"ok": True})
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@app.post("/api/admin/start_game")
def admin_start_game_route():
    read_only_error = _require_writable()
    if read_only_error:
        return read_only_error
    db = _db()
    try:
        cursor = db.get_cursor()
        try:
            cursor.execute(
                "INSERT INTO game (status, created_at) VALUES ('running', NOW())"
            )
            db.commit()
            new_game_id = cursor.lastrowid
        finally:
            cursor.close()
        return jsonify({"ok": True, "game_id": new_game_id})
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@app.post("/api/game/<int:game_id>/property/upgrade_house")
def upgrade_house(game_id: int):
    read_only_error = _require_writable()
    if read_only_error:
        return read_only_error
    payload = request.get_json(silent=True) or {}
    player_id = payload.get("player_id")
    property_id = payload.get("property_id")
    if not player_id or not property_id:
        return jsonify({"error": "player_id and property_id are required"}), 400
    db = _db()
    try:
        prop = _query_one(
            db,
            """
            SELECT pr.property_id, pr.name, pr.houses, pr.houseCost, pr.isMortgaged
            FROM property pr
            JOIN ownership o ON o.property_id = pr.property_id AND o.end_time IS NULL
            JOIN player p ON p.player_id = o.player_id
            WHERE p.game_id = %s AND o.player_id = %s AND pr.property_id = %s
            """,
            (game_id, player_id, property_id),
        )
        if not prop:
            return jsonify({"error": "Property not owned by player"}), 400
        if prop["isMortgaged"]:
            return jsonify({"error": "Cannot upgrade mortgaged property"}), 400
        if int(prop["houses"] or 0) >= 5:
            return jsonify({"error": "Property already at max house level"}), 400
        house_cost = int(prop.get("houseCost") or 0)
        if house_cost <= 0:
            return jsonify({"error": "This property cannot be upgraded"}), 400
        bal = _query_one(db, "SELECT balance FROM player WHERE player_id = %s", (player_id,))
        if not bal or int(bal["balance"]) < house_cost:
            return jsonify({"error": "Insufficient balance"}), 400

        record_transaction(db, game_id, int(player_id), None, house_cost, "purchase")
        cursor = db.get_cursor()
        try:
            cursor.execute("UPDATE property SET houses = houses + 1 WHERE property_id = %s", (property_id,))
        finally:
            cursor.close()
        record_game_event(db, game_id, "transaction", f"Player {player_id} upgraded property {property_id}.")
        db.commit()
        return jsonify({"ok": True})
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@app.post("/api/game/<int:game_id>/property/downgrade_house")
def downgrade_house(game_id: int):
    read_only_error = _require_writable()
    if read_only_error:
        return read_only_error
    payload = request.get_json(silent=True) or {}
    player_id = payload.get("player_id")
    property_id = payload.get("property_id")
    if not player_id or not property_id:
        return jsonify({"error": "player_id and property_id are required"}), 400
    db = _db()
    try:
        prop = _query_one(
            db,
            """
            SELECT pr.property_id, pr.name, pr.houses, pr.houseCost
            FROM property pr
            JOIN ownership o ON o.property_id = pr.property_id AND o.end_time IS NULL
            JOIN player p ON p.player_id = o.player_id
            WHERE p.game_id = %s AND o.player_id = %s AND pr.property_id = %s
            """,
            (game_id, player_id, property_id),
        )
        if not prop:
            return jsonify({"error": "Property not owned by player"}), 400
        if int(prop["houses"] or 0) <= 0:
            return jsonify({"error": "No house to remove"}), 400

        cursor = db.get_cursor()
        try:
            cursor.execute("UPDATE property SET houses = houses - 1 WHERE property_id = %s", (property_id,))
        finally:
            cursor.close()
        refund = int((prop.get("houseCost") or 0) // 2)
        if refund > 0:
            record_transaction(db, game_id, None, int(player_id), refund, "reward")
        record_game_event(db, game_id, "transaction", f"Player {player_id} downgraded property {property_id}.")
        db.commit()
        return jsonify({"ok": True})
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@app.post("/api/game/<int:game_id>/property/toggle_mortgage")
def toggle_mortgage(game_id: int):
    read_only_error = _require_writable()
    if read_only_error:
        return read_only_error
    payload = request.get_json(silent=True) or {}
    player_id = payload.get("player_id")
    property_id = payload.get("property_id")
    if not player_id or not property_id:
        return jsonify({"error": "player_id and property_id are required"}), 400
    db = _db()
    try:
        prop = _query_one(
            db,
            """
            SELECT pr.property_id, pr.name, pr.houses, pr.isMortgaged, pr.cost
            FROM property pr
            JOIN ownership o ON o.property_id = pr.property_id AND o.end_time IS NULL
            JOIN player p ON p.player_id = o.player_id
            WHERE p.game_id = %s AND o.player_id = %s AND pr.property_id = %s
            """,
            (game_id, player_id, property_id),
        )
        if not prop:
            return jsonify({"error": "Property not owned by player"}), 400
        if int(prop["houses"] or 0) > 0:
            return jsonify({"error": "Cannot mortgage property with houses"}), 400
        cursor = db.get_cursor()
        try:
            if prop["isMortgaged"]:
                fee = int((int(prop["cost"] or 0) // 2) * 1.10)
                bal = _query_one(db, "SELECT balance FROM player WHERE player_id = %s", (player_id,))
                if not bal or int(bal["balance"]) < fee:
                    return jsonify({"error": "Insufficient balance to unmortgage"}), 400
                record_transaction(db, game_id, int(player_id), None, fee, "unmortgage")
                cursor.execute("UPDATE property SET isMortgaged = FALSE WHERE property_id = %s", (property_id,))
            else:
                gain = int(prop["cost"] or 0) // 2
                cursor.execute("UPDATE property SET isMortgaged = TRUE WHERE property_id = %s", (property_id,))
                if gain > 0:
                    record_transaction(db, game_id, None, int(player_id), gain, "mortgage")
        finally:
            cursor.close()
        db.commit()
        return jsonify({"ok": True})
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@app.get("/api/game/<int:game_id>/trade/incoming")
def trade_incoming(game_id: int):
    player_id = request.args.get("player_id", type=int)
    if not player_id:
        return jsonify({"error": "player_id query required"}), 400
    db = _db()
    try:
        trades = _query_all(
            db,
            """
            SELECT t.trade_id, t.proposer_id, p.name AS proposer_name, t.offeredCash, t.requestedCash, t.status
            FROM trade t
            JOIN player p ON t.proposer_id = p.player_id
            WHERE t.receiver_id = %s AND t.status = 'pending' AND t.game_id = %s
            ORDER BY t.trade_id
            """,
            (player_id, game_id),
        )
        return jsonify({"trades": trades})
    finally:
        db.close()


@app.get("/api/game/<int:game_id>/trade/<int:trade_id>")
def trade_detail(game_id: int, trade_id: int):
    db = _db()
    try:
        row = _query_one(
            db,
            """
            SELECT t.trade_id, t.proposer_id, t.receiver_id, t.offeredCash, t.requestedCash, t.status,
                   pp.name AS proposer_name, rp.name AS receiver_name
            FROM trade t
            JOIN player pp ON t.proposer_id = pp.player_id
            JOIN player rp ON t.receiver_id = rp.player_id
            WHERE t.trade_id = %s AND t.game_id = %s
            """,
            (trade_id, game_id),
        )
        if not row:
            return jsonify({"error": "Trade not found"}), 404
        offers = _query_all(
            db,
            """
            SELECT p.property_id, p.name, p.propSet, p.cost
            FROM property p
            JOIN trade_offers tro ON p.property_id = tro.property_id
            WHERE tro.trade_id = %s
            """,
            (trade_id,),
        )
        reqs = _query_all(
            db,
            """
            SELECT p.property_id, p.name, p.propSet, p.cost
            FROM property p
            JOIN trade_requests trr ON p.property_id = trr.property_id
            WHERE trr.trade_id = %s
            """,
            (trade_id,),
        )
        return jsonify({"trade": row, "offer_properties": offers, "request_properties": reqs})
    finally:
        db.close()


@app.post("/api/game/<int:game_id>/trade/create")
def trade_create(game_id: int):
    read_only_error = _require_writable()
    if read_only_error:
        return read_only_error
    payload = request.get_json(silent=True) or {}
    proposer_id = payload.get("proposer_id")
    receiver_id = payload.get("receiver_id")
    offered_cash = int(payload.get("offered_cash") or 0)
    requested_cash = int(payload.get("requested_cash") or 0)
    offer_property_ids = payload.get("offer_property_ids") or []
    request_property_ids = payload.get("request_property_ids") or []
    if not proposer_id or not receiver_id or int(proposer_id) == int(receiver_id):
        return jsonify({"error": "proposer_id and receiver_id required"}), 400
    if offered_cash < 0 or requested_cash < 0:
        return jsonify({"error": "Cash amounts must be non-negative"}), 400

    db = _db()
    try:
        p1 = _query_one(db, "SELECT game_id FROM player WHERE player_id = %s", (proposer_id,))
        p2 = _query_one(db, "SELECT game_id FROM player WHERE player_id = %s", (receiver_id,))
        if not p1 or not p2 or int(p1["game_id"]) != game_id or int(p2["game_id"]) != game_id:
            return jsonify({"error": "Players must belong to this game"}), 400

        for pid in offer_property_ids:
            own = _query_one(
                db,
                """
                SELECT o.player_id FROM ownership o
                WHERE o.property_id = %s AND o.end_time IS NULL
                """,
                (int(pid),),
            )
            if not own or int(own["player_id"]) != int(proposer_id):
                return jsonify({"error": f"Offered property {pid} not owned by proposer"}), 400

        for pid in request_property_ids:
            own = _query_one(
                db,
                """
                SELECT o.player_id FROM ownership o
                WHERE o.property_id = %s AND o.end_time IS NULL
                """,
                (int(pid),),
            )
            if not own or int(own["player_id"]) != int(receiver_id):
                return jsonify({"error": f"Requested property {pid} not owned by receiver"}), 400

        cursor = db.get_cursor()
        try:
            cursor.execute("SELECT COALESCE(MAX(trade_id), 0) + 1 AS next_id FROM trade")
            trade_id = cursor.fetchone()["next_id"]
            cursor.execute(
                """
                INSERT INTO trade (trade_id, status, offeredCash, requestedCash, negotiationRound, proposer_id, receiver_id, game_id)
                VALUES (%s, 'pending', %s, %s, 0, %s, %s, %s)
                """,
                (trade_id, offered_cash, requested_cash, proposer_id, receiver_id, game_id),
            )
            for pid in offer_property_ids:
                cursor.execute(
                    "INSERT INTO trade_offers (trade_id, property_id) VALUES (%s, %s)",
                    (trade_id, int(pid)),
                )
            for pid in request_property_ids:
                cursor.execute(
                    "INSERT INTO trade_requests (trade_id, property_id) VALUES (%s, %s)",
                    (trade_id, int(pid)),
                )
            db.commit()
        finally:
            cursor.close()
        return jsonify({"ok": True, "trade_id": trade_id})
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


@app.post("/api/game/<int:game_id>/trade/<int:trade_id>/respond")
def trade_respond(game_id: int, trade_id: int):
    read_only_error = _require_writable()
    if read_only_error:
        return read_only_error
    payload = request.get_json(silent=True) or {}
    player_id = payload.get("player_id")
    accept = payload.get("accept")
    if player_id is None or accept is None:
        return jsonify({"error": "player_id and accept required"}), 400

    db = _db()
    try:
        t = _query_one(
            db,
            """
            SELECT trade_id, proposer_id, receiver_id, offeredCash, requestedCash, status
            FROM trade WHERE trade_id = %s AND game_id = %s
            """,
            (trade_id, game_id),
        )
        if not t:
            return jsonify({"error": "Trade not found"}), 404
        if t["status"] != "pending":
            return jsonify({"error": "Trade is no longer pending"}), 400
        if int(t["receiver_id"]) != int(player_id):
            return jsonify({"error": "Only the receiver can respond"}), 403

        if accept:
            _process_trade_acceptance_direct(
                db,
                game_id,
                trade_id,
                int(t["proposer_id"]),
                int(t["receiver_id"]),
                int(t["offeredCash"] or 0),
                int(t["requestedCash"] or 0),
            )
        else:
            cursor = db.get_cursor()
            try:
                cursor.execute("UPDATE trade SET status = 'declined' WHERE trade_id = %s", (trade_id,))
                record_game_event(db, game_id, "trade", f"Trade #{trade_id} declined by Player {player_id}.")
                db.commit()
            finally:
                cursor.close()
        return jsonify({"ok": True})
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as exc:
        db.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        db.close()


if __name__ == "__main__":
    app.run(debug=True)

from __future__ import annotations

from typing import Any


def update_alert_by_id(db_client: Any, alert_id: str, value: float) -> bool:
    return bool(db_client.update_alert_target(alert_id, value))


def delete_alert_by_id(db_client: Any, alert_id: str) -> bool:
    return bool(db_client.delete_alert_db(alert_id=alert_id))


def restore_alert_by_id(db_client: Any, alert_id: str) -> bool:
    return bool(db_client.restore_alert_db(alert_id))


def toggle_alert(db_client: Any, alert_id: str, is_active: bool) -> bool:
    return bool(db_client.toggle_alert_active(alert_id, is_active))


def get_deleted_alerts(db_client: Any):
    return db_client.get_deleted_alerts_db()


def get_alert_history(db_client: Any, limit: int = 50):
    return db_client.get_alert_history_db(limit=limit)

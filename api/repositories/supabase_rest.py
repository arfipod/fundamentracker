from __future__ import annotations

import os
import logging
from uuid import UUID
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import requests

from repositories.base import (
    DEFAULT_TIMEOUT_SECONDS,
    METRIC_SNAPSHOT_COLUMNS,
    PROVIDER_HEALTH_COLUMNS,
    DatabaseHealthError,
    build_watchlist,
    serialize_value,
)

logger = logging.getLogger(__name__)


class SupabaseRestRepository:
    DatabaseHealthError = DatabaseHealthError
    backend = "supabase_rest"
    ALERT_COLUMNS = (
        "id,ticker_symbol,metric,operator,target_value,is_active,"
        "is_triggered,reference_value,alert_type,current_value,"
        "current_source,current_as_of_date,current_fetched_at,"
        "current_expires_at,current_stale,current_confidence,"
        "deleted_at,restored_at,created_at"
    )
    TICKER_COLUMNS = (
        "symbol,name,status,priority,notes,thesis,target_action,created_at,updated_at"
    )

    def __init__(
        self,
        *,
        supabase_url: str | None = None,
        supabase_key: str | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        requests_client: Any = requests,
    ):
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.timeout_seconds = timeout_seconds
        self.requests = requests_client

    def _get_config(self) -> tuple[str | None, str | None]:
        return self.supabase_url or os.getenv("SUPABASE_URL"), self.supabase_key or os.getenv(
            "SUPABASE_KEY"
        )

    def _headers(self) -> dict[str, str]:
        _, supabase_key = self._get_config()
        return {
            "apikey": supabase_key or "",
            "Authorization": f"Bearer {supabase_key or ''}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _encode_filter_value(value: Any) -> str:
        return quote(str(serialize_value(value)), safe="")

    def _req(self, method: str, endpoint: str, **kwargs):
        supabase_url, supabase_key = self._get_config()
        if not supabase_url or not supabase_key:
            return [] if method == "GET" else None

        url = f"{supabase_url}/rest/v1/{endpoint}"
        headers = self._headers()
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        kwargs.setdefault("timeout", self.timeout_seconds)

        try:
            response = self.requests.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            if method != "DELETE":
                if response.text.strip() == "":
                    return []
                return response.json()
            return True
        except requests.exceptions.RequestException as error:
            status_code = error.response.status_code if error.response is not None else None
            response_text = error.response.text[:500] if error.response is not None else None
            logger.warning(
                "Supabase REST request failed",
                extra={
                    "database_backend": self.backend,
                    "method": method,
                    "endpoint": endpoint.split("?")[0],
                    "status_code": status_code,
                    "response_text": response_text,
                },
                exc_info=error,
            )
            return [] if method == "GET" else None

    def is_configured(self) -> bool:
        supabase_url, supabase_key = self._get_config()
        return bool(supabase_url and supabase_key)

    def check_connectivity(self) -> dict[str, str]:
        supabase_url, supabase_key = self._get_config()
        if not supabase_url or not supabase_key:
            raise DatabaseHealthError(
                reason="not_configured",
                detail="SUPABASE_URL and SUPABASE_KEY must be configured.",
                backend=self.backend,
            )

        url = f"{supabase_url}/rest/v1/scan_settings"
        params = {"select": "id", "id": "eq.1", "limit": "1"}

        try:
            response = self.requests.get(
                url,
                headers=self._headers(),
                params=params,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.exceptions.Timeout as exc:
            raise DatabaseHealthError(
                reason="timeout",
                detail="Database readiness check timed out.",
                backend=self.backend,
            ) from exc
        except requests.exceptions.RequestException as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            detail = "Database readiness check failed."
            if status_code is not None:
                detail = f"{detail} Upstream status: {status_code}."
            raise DatabaseHealthError(
                reason="connection_failed",
                detail=detail,
                backend=self.backend,
            ) from exc

        return {
            "status": "ok",
            "backend": self.backend,
        }

    def check_database_connectivity(self) -> dict[str, str]:
        return self.check_connectivity()

    def get_watchlist(self):
        tickers = self._req("GET", f"tickers?select={self.TICKER_COLUMNS}&order=symbol.asc") or []
        alerts = (
            self._req(
                "GET",
                f"alerts?select={self.ALERT_COLUMNS}&deleted_at=is.null&order=created_at.asc",
            )
            or []
        )
        ticker_tags = (
            self._req(
                "GET",
                "ticker_tags?select=ticker_symbol,tags(id,name,color)",
            )
            or []
        )
        return build_watchlist(tickers, alerts, ticker_tags)

    def get_alerts(self):
        return (
            self._req(
                "GET",
                f"alerts?select={self.ALERT_COLUMNS}&deleted_at=is.null&order=created_at.asc",
            )
            or []
        )

    def get_fresh_metric_snapshot(
        self,
        symbol: str,
        metric: str,
        now: datetime,
    ) -> dict[str, Any] | None:
        symbol = symbol.upper()
        metric = metric.lower()

        rows = (
            self._req(
                "GET",
                "metric_snapshots"
                f"?select={METRIC_SNAPSHOT_COLUMNS}"
                f"&symbol=eq.{self._encode_filter_value(symbol)}"
                f"&metric=eq.{self._encode_filter_value(metric)}"
                f"&expires_at=gt.{self._encode_filter_value(now)}"
                "&order=fetched_at.desc"
                "&limit=1",
            )
            or []
        )
        return rows[0] if rows else None

    def get_latest_metric_snapshot(self, symbol: str, metric: str) -> dict[str, Any] | None:
        symbol = symbol.upper()
        metric = metric.lower()

        rows = (
            self._req(
                "GET",
                "metric_snapshots"
                f"?select={METRIC_SNAPSHOT_COLUMNS}"
                f"&symbol=eq.{self._encode_filter_value(symbol)}"
                f"&metric=eq.{self._encode_filter_value(metric)}"
                "&order=fetched_at.desc"
                "&limit=1",
            )
            or []
        )
        return rows[0] if rows else None

    def save_metric_snapshot(self, snapshot: dict[str, Any]) -> dict[str, Any] | None:
        payload = {
            "symbol": snapshot.get("symbol", "").upper(),
            "metric": snapshot.get("metric", "").lower(),
            "value": snapshot.get("value"),
            "unit": snapshot.get("unit"),
            "currency": snapshot.get("currency"),
            "source": snapshot.get("source"),
            "as_of_date": serialize_value(snapshot.get("as_of_date")),
            "fetched_at": serialize_value(snapshot.get("fetched_at")),
            "expires_at": serialize_value(snapshot.get("expires_at")),
            "confidence": snapshot.get("confidence"),
            "raw_payload": snapshot.get("raw_payload"),
        }

        headers = {"Prefer": "return=representation"}
        rows = self._req("POST", "metric_snapshots", json=payload, headers=headers) or []
        return rows[0] if rows else None

    def upsert_provider_health(
        self,
        provider: str,
        status: str,
        *,
        last_ok_at: datetime | None = None,
        last_error_at: datetime | None = None,
        last_error: str | None = None,
    ) -> dict[str, Any] | None:
        payload = {
            "provider": provider,
            "status": status,
            "last_ok_at": serialize_value(last_ok_at),
            "last_error_at": serialize_value(last_error_at),
            "last_error": last_error,
        }

        headers = {"Prefer": "resolution=merge-duplicates, return=representation"}
        clean_payload = {key: value for key, value in payload.items() if value is not None}
        rows = self._req("POST", "provider_health", json=clean_payload, headers=headers) or []
        return rows[0] if rows else None

    def get_provider_health(self) -> list[dict[str, Any]]:
        return (
            self._req(
                "GET",
                f"provider_health?select={PROVIDER_HEALTH_COLUMNS}&order=provider.asc",
            )
            or []
        )

    def get_tickers(self):
        return self._req("GET", f"tickers?select={self.TICKER_COLUMNS}&order=symbol.asc") or []

    def get_tags(self):
        return self._req("GET", "tags?select=id,name,color,created_at&order=name.asc") or []

    def add_ticker_db(self, symbol, company_name):
        headers = {"Prefer": "resolution=merge-duplicates, return=representation"}
        payload = {"symbol": symbol, "name": company_name}
        return self._req("POST", "tickers?on_conflict=symbol", json=payload, headers=headers)

    def update_ticker_metadata(self, symbol, metadata):
        allowed_columns = ("status", "priority", "notes", "thesis", "target_action")
        payload = {key: metadata[key] for key in allowed_columns if key in metadata}
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        headers = {"Prefer": "return=representation"}
        rows = self._req(
            "PATCH",
            f"tickers?symbol=eq.{self._encode_filter_value(symbol)}",
            json=payload,
            headers=headers,
        )
        return rows[0] if rows else None

    def _get_tag_by_name_or_id(self, tag_name_or_id):
        try:
            UUID(str(tag_name_or_id))
        except ValueError:
            pass
        else:
            rows = (
                self._req(
                    "GET",
                    "tags"
                    "?select=id,name,color,created_at"
                    f"&id=eq.{self._encode_filter_value(tag_name_or_id)}"
                    "&limit=1",
                )
                or []
            )
            if rows:
                return rows[0]

        rows = (
            self._req(
                "GET",
                "tags"
                "?select=id,name,color,created_at"
                f"&name=eq.{self._encode_filter_value(tag_name_or_id)}"
                "&limit=1",
            )
            or []
        )
        return rows[0] if rows else None

    def add_tag_to_ticker(self, symbol, name, color=None):
        existing = self._get_tag_by_name_or_id(name)
        if existing is None:
            tag_payload = {"name": name}
            if color is not None:
                tag_payload["color"] = color
            headers = {"Prefer": "resolution=merge-duplicates, return=representation"}
            rows = (
                self._req(
                    "POST",
                    "tags?on_conflict=name",
                    json=tag_payload,
                    headers=headers,
                )
                or []
            )
            tag = rows[0] if rows else None
        else:
            tag = existing
            if color is not None and color != tag.get("color"):
                headers = {"Prefer": "return=representation"}
                rows = (
                    self._req(
                        "PATCH",
                        f"tags?id=eq.{self._encode_filter_value(tag['id'])}",
                        json={"color": color},
                        headers=headers,
                    )
                    or []
                )
                tag = rows[0] if rows else tag

        if tag is None:
            return None

        headers = {"Prefer": "resolution=ignore-duplicates"}
        self._req(
            "POST",
            "ticker_tags?on_conflict=ticker_symbol,tag_id",
            json={"ticker_symbol": symbol, "tag_id": tag["id"]},
            headers=headers,
        )
        return tag

    def remove_tag_from_ticker(self, symbol, tag_name_or_id):
        tag = self._get_tag_by_name_or_id(tag_name_or_id)
        if tag is None:
            return False
        return bool(
            self._req(
                "DELETE",
                "ticker_tags"
                f"?ticker_symbol=eq.{self._encode_filter_value(symbol)}"
                f"&tag_id=eq.{self._encode_filter_value(tag['id'])}",
            )
        )

    def add_alert_db(
        self,
        symbol,
        metric,
        operator,
        target_value,
        alert_type="absolute",
        reference_value=None,
    ):
        payload = {
            "ticker_symbol": symbol,
            "metric": metric,
            "operator": operator,
            "target_value": target_value,
            "alert_type": alert_type,
            "reference_value": reference_value,
            "is_active": True,
            "is_triggered": False,
        }
        headers = {"Prefer": "return=representation"}
        return self._req("POST", "alerts", json=payload, headers=headers)

    def update_alert_target(self, alert_id, new_target):
        payload = {"target_value": float(new_target)}
        headers = {"Prefer": "return=representation"}
        return self._req(
            "PATCH",
            f"alerts?id=eq.{alert_id}&deleted_at=is.null",
            json=payload,
            headers=headers,
        )

    def toggle_alert_active(self, alert_id, is_active):
        payload = {"is_active": is_active}
        headers = {"Prefer": "return=representation"}
        return self._req(
            "PATCH",
            f"alerts?id=eq.{alert_id}&deleted_at=is.null",
            json=payload,
            headers=headers,
        )

    def restore_alert_db(self, alert_id):
        payload = {
            "deleted_at": None,
            "restored_at": datetime.now(timezone.utc).isoformat(),
        }
        headers = {"Prefer": "return=representation"}
        return self._req("PATCH", f"alerts?id=eq.{alert_id}", json=payload, headers=headers)

    def get_deleted_alerts_db(self):
        return (
            self._req(
                "GET",
                f"alerts?select={self.ALERT_COLUMNS}&deleted_at=not.is.null&order=deleted_at.desc",
            )
            or []
        )

    def update_alert_status(self, alert_id, is_triggered, current_value=None, current_metadata=None):
        current_metadata = current_metadata or {}
        payload = {"is_triggered": is_triggered}
        if current_value is not None:
            payload["current_value"] = float(current_value)
            payload["current_source"] = current_metadata.get("source")
            payload["current_as_of_date"] = serialize_value(current_metadata.get("as_of_date"))
            payload["current_fetched_at"] = serialize_value(current_metadata.get("fetched_at"))
            payload["current_expires_at"] = serialize_value(current_metadata.get("expires_at"))
            payload["current_stale"] = current_metadata.get("stale")
            payload["current_confidence"] = current_metadata.get("confidence")
            payload = {key: value for key, value in payload.items() if value is not None}
        headers = {"Prefer": "return=representation"}
        return self._req(
            "PATCH",
            f"alerts?id=eq.{alert_id}&deleted_at=is.null",
            json=payload,
            headers=headers,
        )

    def delete_alert_db(self, alert_id=None, symbol=None, metric=None):
        payload = {"deleted_at": datetime.now(timezone.utc).isoformat()}
        headers = {"Prefer": "return=representation"}
        if alert_id:
            return self._req("PATCH", f"alerts?id=eq.{alert_id}", json=payload, headers=headers)
        if symbol and metric:
            return self._req(
                "PATCH",
                f"alerts?ticker_symbol=eq.{symbol}&metric=eq.{metric}&deleted_at=is.null",
                json=payload,
                headers=headers,
            )
        return False

    def delete_ticker_db(self, symbol):
        return self._req("DELETE", f"tickers?symbol=eq.{symbol}")

    def get_scan_settings_db(self):
        res = self._req("GET", "scan_settings?id=eq.1")
        if res and len(res) > 0:
            return res[0]
        return {"interval_seconds": 0, "last_scan_time": 0}

    def update_scan_settings_db(self, interval=None, last_scan_time=None):
        payload = {}
        if interval is not None:
            payload["interval_seconds"] = interval
        if last_scan_time is not None:
            payload["last_scan_time"] = last_scan_time

        headers = {"Prefer": "return=representation"}
        res = self._req("PATCH", "scan_settings?id=eq.1", json=payload, headers=headers)
        if res and len(res) > 0:
            return res[0]
        return {}

    def log_alert_history(self, alert_id, trigger_val, target_val, metadata=None):
        metadata = metadata or {}
        payload = {
            "alert_id": alert_id,
            "trigger_value": trigger_val,
            "target_value": target_val,
            "ticker_symbol": metadata.get("ticker_symbol"),
            "company_name": metadata.get("company_name"),
            "metric": metadata.get("metric"),
            "operator": metadata.get("operator"),
            "alert_type": metadata.get("alert_type"),
            "reference_value": metadata.get("reference_value"),
            "current_value": metadata.get("current_value", trigger_val),
            "source": metadata.get("source"),
            "as_of_date": serialize_value(metadata.get("as_of_date")),
            "fetched_at": serialize_value(metadata.get("fetched_at")),
            "message": metadata.get("message"),
        }
        payload = {key: value for key, value in payload.items() if value is not None}
        headers = {"Prefer": "return=representation"}
        return self._req("POST", "alert_history", json=payload, headers=headers)

    def get_alert_history_db(self, limit=50):
        return (
            self._req(
                "GET",
                f"alert_history?select=*,alerts(ticker_symbol,metric)&order=triggered_at.desc&limit={limit}",
            )
            or []
        )


def default_state():
    return {
        "watchlist": {}, 
        "last_update_id": 0,
        "scan_settings": {
            "interval_seconds": 0,
            "last_scan_time": 0
        }
    }


def ensure_state_shape(state):
    if not isinstance(state, dict):
        return default_state()

    if "watchlist" not in state or "last_update_id" not in state:
        return default_state()

    if "scan_settings" not in state:
        state["scan_settings"] = {"interval_seconds": 0, "last_scan_time": 0}

    return state


def default_state():
    return {"watchlist": {}, "last_update_id": 0}


def ensure_state_shape(state):
    if not isinstance(state, dict):
        return default_state()

    if "watchlist" not in state or "last_update_id" not in state:
        return default_state()

    return state

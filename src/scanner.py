from config import OPERATORS_MAP
try:
    from watchlist import fetch_metric
except Exception:
    pass

from db import client as db

def run_fundamental_scan(send_alert_func):
    """
    1) Fetches watchlist from db
    2) Performs logic for each alert
    3) Triggers log & updates if condition met
    """
    watchlist = db.get_watchlist()
    
    symbols = list(watchlist.keys())
    if not symbols:
        return
        
    for ticker, details in list(watchlist.items()):
        
        for alert in details.get("alerts", []):
            if not alert.get("is_active", True):
                # Always update the status as False if not active to avoid ghost states? Or just leave it. 
                # Better left as is.
                continue
                
            current_val = fetch_metric(ticker, alert["metric"])
            if current_val is None:
                continue
                
            op_func = OPERATORS_MAP.get(alert["operator"])
            if not op_func:
                continue
                
            is_triggered = False
            
            # Relative vs Absolute logic
            if alert.get("alert_type") == "relative" and alert.get("reference_value") is not None:
                diff = ((current_val / alert["reference_value"]) - 1) * 100
                is_triggered = op_func(diff, alert["target"])
            else:
                is_triggered = op_func(current_val, alert["target"])
                
            # Update DB with new value and trigger state
            db.update_alert_status(alert["id"], is_triggered, current_val)
            
            # If crossed from untriggered to triggered
            if is_triggered and not alert.get("is_triggered", False):
                # Triggered! Log to history
                db.log_alert_history(alert["id"], current_val, alert["target"])
                
                # Format message
                if alert.get("alert_type") == "relative":
                    msg = f"🚨 *{details['name']}* ({ticker}): {alert['metric'].upper()} changed by {alert['operator']} {alert['target']}% (Current: {current_val:.2f}, Ref: {alert['reference_value']:.2f})"
                else:    
                    msg = f"🚨 *{details['name']}* ({ticker}): {alert['metric'].upper()} {alert['operator']} {alert['target']} (Current: {current_val:.2f})"
                    
                send_alert_func(msg)

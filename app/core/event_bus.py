"""Qt signal bridge — app-wide event bus backed by a singleton QObject."""
from PySide6.QtCore import QObject, Signal


class _EventBus(QObject):
    # campaign progress
    send_progress = Signal(int, int, str)       # campaign_id, sent_count, recipient_email
    send_complete = Signal(int)                  # campaign_id
    send_error = Signal(int, str, str)           # campaign_id, recipient_email, error_msg

    # import progress
    import_progress = Signal(int, int)           # current, total
    import_complete = Signal(int, str)           # rows_imported, list_name

    # tracking
    tracking_event = Signal(str, str)            # event_type, token

    # general log line for the UI log panel
    log_line = Signal(str)                       # pre-formatted log message


bus = _EventBus()

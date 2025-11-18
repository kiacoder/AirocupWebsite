"""Extionsions of the Website"""
import os
from flask_wtf.csrf import CSRFProtect  # type:ignore
from flask_limiter import Limiter
from flask_socketio import SocketIO
from flask_limiter.util import get_remote_address

csrf_protector = CSRFProtect()
limiter_storage_uri = os.getenv("AIROCUP_RATE_LIMIT_STORAGE", "redis://localhost:6379")
limiter = Limiter(key_func=get_remote_address, storage_uri=limiter_storage_uri)
socket_io = SocketIO()

from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_socketio import SocketIO
from flask_limiter.util import get_remote_address

csrf_protector = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, storage_uri="redis://localhost:6379")
socket_io = SocketIO()

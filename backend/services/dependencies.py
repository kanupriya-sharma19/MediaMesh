"""Application-level service instances shared by API dependencies."""

from backend.services.auth_service import AuthService
from backend.services.chat_service import ChatService


auth_service = AuthService()
chat_service = ChatService()

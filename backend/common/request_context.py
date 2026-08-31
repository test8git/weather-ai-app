from contextvars import ContextVar

#
# Logged-in user
#
current_user_id: ContextVar[str | None] = ContextVar("current_user_id", default=None)

#
# User's Zapier MCP URL
#
current_profile: ContextVar[str | None] = ContextVar("current_profile", default=None)

#
# User's Zapier MCP URL
#
current_selected_ai_modal: ContextVar[str | None] = ContextVar("current_selected_ai_modal", default=None)
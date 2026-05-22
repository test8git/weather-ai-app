SESSION_MEMORY = {}


def save_message(session_id, role, message):

    if session_id not in SESSION_MEMORY:
        SESSION_MEMORY[session_id] = []

    SESSION_MEMORY[session_id].append({
        "role": role,
        "message": message
    })


def get_history(session_id):

    return SESSION_MEMORY.get(session_id, [])
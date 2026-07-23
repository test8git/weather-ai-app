import json

def sse_event(event_type, content):
    return json.dumps({
        "type": event_type,
        "content": content
    })

def sse_step(step, status, icon):
    return json.dumps({
        "type": "step",
        "step": step,
        "status": status,
        "icon": icon
    })
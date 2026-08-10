from langchain_core.messages import HumanMessage
from langchain_core.messages import AIMessage
from memory.conversation_store import ConversationStore


def load_chat_history(conversation_id, exclude_message_id=None):

    rows = ConversationStore.load_messages(conversation_id,exclude_message_id)

    history = []

    for row in rows:

        if row["role"] == "user":

            history.append(

                HumanMessage(content=row["content"])

            )

        elif row["role"] == "assistant":

            history.append(

                AIMessage(content=row["content"])

            )

    return history
from database.client import supabase


class ConversationStore:

    @staticmethod
    def load_messages(conversation_id, exclude_message_id=None):

        query = (
            supabase
            .table("messages")
            .select("*")
            .eq("conversation_id", conversation_id)
        )

        # Exclude the message currently being processed
        if exclude_message_id:
            query = query.neq(
                "id",
                exclude_message_id
            )

        result = (
            query
            .order(
                "created_at",
                desc=True
            )
            .limit(20)
            .execute()
        )

        # We fetched newest → oldest.
        # LangGraph should receive oldest → newest.
        rows = result.data or []

        rows.reverse()

        return rows

    # # # @staticmethod
    # # # def save_message(conversation_id, role, content):

    # # #     supabase.table("messages").insert({
    # # #         "conversation_id": conversation_id,
    # # #         "role": role,
    # # #         "content": content
    # # #     }).execute()
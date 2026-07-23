from database.client import supabase


class ConversationStore:

    @staticmethod
    def load_messages(conversation_id):

        result = (
            supabase
            .table("messages")
            .select("*")
            .eq("conversation_id", conversation_id)
            .order("created_at")
            .limit(20)
            .execute()
        )

        return result.data


    # # # @staticmethod
    # # # def save_message(conversation_id, role, content):

    # # #     supabase.table("messages").insert({
    # # #         "conversation_id": conversation_id,
    # # #         "role": role,
    # # #         "content": content
    # # #     }).execute()
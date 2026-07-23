from client import supabase

result = (
    supabase
        .table("messages")
        .select("*")
        .limit(5)
        .execute()
)

print(result.data)
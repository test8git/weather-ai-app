import { supabase } from "./supabase";

export async function uploadAvatar(userId, file)
{
    const extension = file.name.split(".").pop();

    const fileName = `${userId}.${extension}`;

    const filePath = `avatars/${fileName}`;

    const { error } = await supabase.storage.from("avatars").upload(filePath, file, { upsert: true});

    if (error)
        throw error;

    const { data } = supabase.storage.from("avatars").getPublicUrl(filePath);

    return data.publicUrl;
}

export async function updateProfile(profile)
{
    const {error} = await supabase.from("profiles").update(profile).eq("id", profile.id);

    if (error)
        throw error;
}
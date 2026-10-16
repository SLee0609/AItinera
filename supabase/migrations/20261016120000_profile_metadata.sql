-- Fill profile names and avatars from later sign-ins, not only the first one.
--
-- Signing in with Google using the email of an existing email/password account links the Google identity
-- to that user instead of creating a new one, so `on_auth_user_created` never sees the Google name and
-- picture. Supabase copies them into auth.users.raw_user_meta_data on that sign-in, which this trigger
-- watches. Values already in a profile are kept, so a name the user set isn't overwritten.

-- Google provides `full_name` and `avatar_url`; some providers use `name` and `picture`.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, display_name, avatar_url)
  values (
    new.id,
    coalesce(new.raw_user_meta_data ->> 'full_name', new.raw_user_meta_data ->> 'name'),
    coalesce(new.raw_user_meta_data ->> 'avatar_url', new.raw_user_meta_data ->> 'picture')
  );
  return new;
end;
$$;

create function public.handle_user_metadata_update()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  update public.profiles p
  set
    display_name = coalesce(p.display_name, new.raw_user_meta_data ->> 'full_name', new.raw_user_meta_data ->> 'name'),
    avatar_url = coalesce(p.avatar_url, new.raw_user_meta_data ->> 'avatar_url', new.raw_user_meta_data ->> 'picture')
  where p.id = new.id;
  return new;
end;
$$;

create trigger on_auth_user_metadata_updated
  after update of raw_user_meta_data on auth.users
  for each row
  when (old.raw_user_meta_data is distinct from new.raw_user_meta_data)
  execute function public.handle_user_metadata_update();

-- Backfill profiles created before this migration.
update public.profiles p
set
  display_name = coalesce(p.display_name, u.raw_user_meta_data ->> 'full_name', u.raw_user_meta_data ->> 'name'),
  avatar_url = coalesce(p.avatar_url, u.raw_user_meta_data ->> 'avatar_url', u.raw_user_meta_data ->> 'picture')
from auth.users u
where u.id = p.id;

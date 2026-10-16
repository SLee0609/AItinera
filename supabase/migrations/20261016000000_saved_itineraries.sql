-- Accounts, stored itineraries and saved itineraries.
--
-- The backend reads and writes `itineraries` and `saved_itineraries` with the project's secret key, which
-- bypasses row level security. RLS is on with no policies for those tables, so the browser's publishable
-- key can't read or list them directly.

-- One profile per Supabase Auth user; auth.users holds the credentials.
create table public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  display_name text,
  avatar_url text,
  created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

create policy "Users can read their own profile"
  on public.profiles for select to authenticated
  using ((select auth.uid()) = id);

create policy "Users can update their own profile"
  on public.profiles for update to authenticated
  using ((select auth.uid()) = id)
  with check ((select auth.uid()) = id);

-- Google sign-ins fill `full_name` / `name` and `avatar_url`; email sign-ups leave them empty.
create function public.handle_new_user()
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
    new.raw_user_meta_data ->> 'avatar_url'
  );
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- Every itinerary the backend generates, exactly as it was served. Share links point here.
create table public.itineraries (
  id text primary key check (id ~ '^[A-Za-z0-9_-]{12}$'),
  query text not null,
  city text not null,
  days smallint not null check (days between 1 and 7),
  data jsonb not null,
  created_by uuid references auth.users (id) on delete set null,
  created_at timestamptz not null default now()
);

create index itineraries_created_by_idx on public.itineraries (created_by);

alter table public.itineraries enable row level security;

-- A user's bookmarks of stored itineraries.
create table public.saved_itineraries (
  user_id uuid not null references auth.users (id) on delete cascade,
  itinerary_id text not null references public.itineraries (id) on delete cascade,
  saved_at timestamptz not null default now(),
  primary key (user_id, itinerary_id)
);

create index saved_itineraries_user_saved_at_idx on public.saved_itineraries (user_id, saved_at desc);
create index saved_itineraries_itinerary_id_idx on public.saved_itineraries (itinerary_id);

alter table public.saved_itineraries enable row level security;

-- Explicit privileges, so the schema works whether or not the project exposes new tables to the Data API
-- roles automatically. The secret key (service_role) bypasses RLS but still needs table privileges.
revoke all on public.itineraries, public.saved_itineraries from anon, authenticated;
grant select, insert, update, delete on public.itineraries, public.saved_itineraries to service_role;

revoke all on public.profiles from anon;
grant select, update on public.profiles to authenticated;
grant select, insert, update, delete on public.profiles to service_role;

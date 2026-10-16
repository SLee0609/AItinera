-- Total stops in a stored itinerary, selectable as a computed field (`stop_count`) on `itineraries`.
-- The backend's saved-itineraries list reads it so it doesn't have to fetch whole day plans.
create function public.stop_count(public.itineraries) returns integer
language sql immutable
as $$
  select coalesce(sum(jsonb_array_length(d -> 'stops')), 0)::integer
  from jsonb_array_elements($1.data -> 'dayPlans') d
$$;

revoke all on function public.stop_count(public.itineraries) from public, anon, authenticated;
grant execute on function public.stop_count(public.itineraries) to service_role;

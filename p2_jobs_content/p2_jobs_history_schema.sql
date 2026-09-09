-- Adds history-tracking columns to the existing jobs_unified table.
alter table jobs_unified add column if not exists first_seen_at timestamptz default now();
alter table jobs_unified add column if not exists last_seen_at timestamptz default now();
alter table jobs_unified add column if not exists status text default 'active';

-- Append-only event log: one row per detected change (new/updated/removed).
create table if not exists jobs_unified_events (
  event_id bigint generated always as identity primary key,
  source text not null,
  source_id text not null,
  event_type text not null check (event_type in ('new', 'updated', 'removed')),
  detected_at timestamptz not null default now()
);

alter table jobs_unified_events enable row level security;

create policy "Allow anon read events" on jobs_unified_events for select to anon using (true);
create policy "Allow anon insert events" on jobs_unified_events for insert to anon with check (true);

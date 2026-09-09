create table jobs_unified (
  row_id bigint generated always as identity primary key,
  source text not null,
  source_id text not null,
  title text not null,
  company text not null,
  location text default 'Unknown',
  remote boolean default false,
  tags text[] default '{}',
  salary_raw text default '',
  salary_min numeric,
  salary_max numeric,
  url text not null,
  posted_at text default '',
  fetched_at timestamptz default now(),
  unique (source, source_id)
);

alter table jobs_unified enable row level security;

create policy "Allow anon read" on jobs_unified for select to anon using (true);
create policy "Allow anon insert/upsert" on jobs_unified for insert to anon with check (true);
create policy "Allow anon update" on jobs_unified for update to anon using (true) with check (true);

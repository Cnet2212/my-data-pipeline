create table jobs (
  id bigint primary key,
  title text not null,
  company text not null,
  category text not null,
  job_type text not null,
  location text not null,
  salary text default '',
  url text not null,
  published_at text not null,
  tags text[] default '{}',
  fetched_at timestamptz default now()
);

alter table jobs enable row level security;

create policy "Allow anon read" on jobs for select to anon using (true);
create policy "Allow anon insert/upsert" on jobs for insert to anon with check (true);
create policy "Allow anon update" on jobs for update to anon using (true) with check (true);

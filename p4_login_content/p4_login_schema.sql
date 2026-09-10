create table quotes (
  row_id bigint generated always as identity primary key,
  text text not null,
  author text not null,
  tags text[] default '{}',
  fetched_at timestamptz default now(),
  unique (author, text)
);

alter table quotes enable row level security;

create policy "Allow anon read" on quotes for select to anon using (true);
create policy "Allow anon insert/upsert" on quotes for insert to anon with check (true);
create policy "Allow anon update" on quotes for update to anon using (true) with check (true);

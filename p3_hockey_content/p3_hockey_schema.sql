create table hockey_stats (
  row_id bigint generated always as identity primary key,
  team_name text not null,
  year integer not null,
  wins integer not null check (wins >= 0),
  losses integer not null check (losses >= 0),
  ot_losses integer,  -- nullable: genuinely not tracked before the 1999-2000 season
  win_pct numeric not null check (win_pct >= 0 and win_pct <= 1),
  goals_for integer not null check (goals_for >= 0),
  goals_against integer not null check (goals_against >= 0),
  goal_diff integer not null,
  fetched_at timestamptz default now(),
  unique (team_name, year)
);

alter table hockey_stats enable row level security;

create policy "Allow anon read" on hockey_stats for select to anon using (true);
create policy "Allow anon insert/upsert" on hockey_stats for insert to anon with check (true);
create policy "Allow anon update" on hockey_stats for update to anon using (true) with check (true);

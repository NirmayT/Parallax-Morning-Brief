-- Parallax subscriber database schema
-- Run in Supabase SQL Editor.

create table if not exists public.subscribers (
    id uuid primary key default gen_random_uuid(),
    email text not null unique,
    status text not null default 'pending'
        check (status in ('pending', 'active', 'unsubscribed', 'bounced', 'complained')),
    subscribed_at timestamptz not null default now(),
    confirmed_at timestamptz,
    unsubscribed_at timestamptz,
    confirmation_token uuid not null default gen_random_uuid(),
    unsubscribe_token uuid not null default gen_random_uuid(),
    source text not null default 'website',
    consent_version text not null default 'v1'
);

create index if not exists subscribers_status_idx
    on public.subscribers(status);

create unique index if not exists subscribers_confirmation_token_idx
    on public.subscribers(confirmation_token);

create unique index if not exists subscribers_unsubscribe_token_idx
    on public.subscribers(unsubscribe_token);

alter table public.subscribers enable row level security;

-- No browser/client policies are intentionally created.
-- Website API routes and the Python pipeline must access this table only
-- from trusted server-side environments using secret/service-role credentials.

revoke all on table public.subscribers from anon, authenticated;
grant all on table public.subscribers to service_role;
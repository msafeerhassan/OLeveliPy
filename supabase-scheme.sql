insert into storage.buckets (id, name, public)
values ('papers', 'papers', false)
on conflict (id) do nothing;

insert into storage.buckets (id, name, public)
values ('answer-uploads', 'answer-uploads', false)
on conflict (id) do nothing;

create table if not exists grading_history (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users(id) not null,
    subject_name text,
    subject_code text,
    examination_year text,
    examination_series text,
    variant text,
    question_number text,
    topic text,
    marks_awarded int,
    marks_total int,
    result_json jsonb,
    created_at timestamptz default now()
);

create table if not exists coach_chat_history (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users(id) not null,
    role text not null,
    content text not null,
    created_at timestamptz default now()
);

create table if not exists flashcards (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users(id) not null,
    source_entry_id uuid references grading_history(id) on delete set null,
    subject_name text,
    topic text,
    front text not null,
    back text not null,
    interval_days int default 1,
    ease_factor float default 2.5,
    next_review_date date default current_date,
    created_at timestamptz default now()
);

create table if not exists practice_questions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users(id) not null,
    subject_name text not null,
    topic text not null,
    question_text text not null,
    marks_total int not null,
    mark_scheme_path text not null,
    created_at timestamptz default now()
);

alter table grading_history enable row level security;
alter table coach_chat_history enable row level security;
alter table flashcards enable row level security;
alter table practice_questions enable row level security;

create policy "Users can access their own grading history"
    on grading_history for all
    using (auth.uid() = user_id);

create policy "Users can access their own chat history"
    on coach_chat_history for all
    using (auth.uid() = user_id);

create policy "Users can access their own flashcards"
    on flashcards for all
    using (auth.uid() = user_id);

create policy "Users can access their own practice questions"
    on practice_questions for all
    using (auth.uid() = user_id);

create policy "Allow service role full access to papers"
    on storage.objects for all
    to service_role
    using (bucket_id = 'papers')
    with check (bucket_id = 'papers');

create policy "Allow service select on papers"
    on storage.objects for select
    to service_role
    using (bucket_id = 'papers');

create policy "Allow service role full access to answer-uploads"
    on storage.objects for all
    to service_role
    using (bucket_id = 'answer-uploads')
    with check (bucket_id = 'answer-uploads');

create policy "Allow service role select on answer-uploads"
    on storage.objects for select
    to service_role
    using (bucket_id = 'answer-uploads');


NOTIFY pgrst, 'reload schema';
create table grading_history (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users(id) not null,
    subject_name text,
    subject_code text,
    examination_year text,
    examination_series text,
    variant text,
    question_number text,
    marks_awarded int,
    marks_total int,
    result_json jsonb,
    created_at timestamptz default now()
);

create table coach_chat_history (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users(id) not null,
    role text not null,
    context text not null,
    created_at timestamptz default now()
);

alter table grading_history enable row level security;
alter table coach_chat_history enable row level security;

create policy "Users can access their own grading history"
    on grading_history for all
    using (auth.uid() = user_id);

create policy "Users can access their own chat history"
    on coach_chat_history for all
    using (auth.uid() = user_id);
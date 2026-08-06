# OLeveliPy

## An AI-Powered O Level Study Assistant

### Python

#### Features:
1. Fetch any official CAIE O Level Question Paper or Mark Scheme by Subject, Examination Year, Examination Series and Variant
2. AI-Powered Grading of Handwritten or Typed Answers against the real Mark Scheme
3. Grade a Single Question or an Entire Solved Past Paper at Once.
4. AI Auto-segmentation of Multi-Questions Scripts
5. Grading History Stored in Supabase with Full Mark Scheme Breakdown per Question
6. Weak Topics Analysis Dashboard
7. Downloadable PDF Progress Report with Summary Statistics and Topic Breakdown
8. AI Coach Chat with Memory and Full Data Access
9. Directly refer any graded Question straight to AI Coach Chat.
10. Flashcards for wrong questions - SM-2 Algorithm implemented
11. AI-Generated Practice Questions graded against AI-Generated Mark Schemes (as per official SLO's whenever available)
12. Home Dashboard Page with Summarized Data
13. Email and Password Based Authentication
14. Modern and Responsive Design

#### How to test it online:
Here it is: []()

#### How to use it locally:
1. Clone the repository and open the project folder.
2. Install dependancies using: `pip install -r requirements.txt`
3. Create a Supabase Project
4. In Supabase Project, create two private Storage Buckets named: `papers` and `answer-uploads`.
5. Disable `Confirm Email` toggle button in Settings under Authentication.
6. Run the script present inside `supabase-schema.sql` in your Supabase Project SQL Editor.
7. Create a `.env` file in the root folder with your credentials.
8. Run the app using `py main.py`.
9. Enjoy :)

#### Screenshots
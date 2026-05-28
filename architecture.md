# Architecture

## Backend

Pattern: Modular Monolith (REST)

Structure:

app/ auth/ workouts/ exercises/ core/ database.py main.py

## Database Schema

User - id - email - hashed_password - created_at

Exercise - id - name - muscle_group - created_at

Workout - id - user_id - name - date - created_at

WorkoutExercise - id - workout_id - exercise_id

Set - id - workout_exercise_id - reps - weight - order_index

## Authentication

JWT Bearer tokens

## Future Scalability

-   Replace SQLite with PostgreSQL
-   Add Alembic
-   Deploy on Render

# API Contract

Base URL: /api

Auth: POST /auth/register POST /auth/login GET /auth/me

Exercises: GET /exercises

Workouts: GET /workouts POST /workouts GET /workouts/{id} PUT
/workouts/{id} DELETE /workouts/{id}

Sets: POST /sets PUT /sets/{id} DELETE /sets/{id}

Response Format:

{ "success": true, "data": {}, "error": null }

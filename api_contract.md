> **STALE / dangerous.** `POST /sets` and `PUT /sets/{id}` do **not** exist.
> Authoritative surface: `docs/AI_HANDOFF.md` §2.6. Granular Set APIs only.

# API Contract

Base URL: /api

Auth: POST /auth/register POST /auth/login GET /auth/me

Exercises: GET /exercises

Workouts: GET /workouts POST /workouts GET /workouts/{id} PUT
/workouts/{id} DELETE /workouts/{id}

Sets: POST /sets PUT /sets/{id} DELETE /sets/{id}

Response Format:

{ "success": true, "data": {}, "error": null }

import { z } from 'zod';

/**
 * Schemi Zod condivisi dai form di autenticazione.
 *
 * COS'E' ZOD: una libreria che definisce "regole" sui dati. Da uno schema
 * ricaviamo automaticamente la validazione + i messaggi d'errore. Il form
 * (react-hook-form) usa questi schemi per decidere se i dati sono "corretti"
 * PRIMA di chiamare il backend.
 *
 * Rispecchia il contratto del backend (vedi backend/app/auth/schemas.py):
 *   - register: email valida + password (min 8 caratteri)
 *   - login:    email valida + password (non vuota)
 */

// Regola riutilizzabile per il campo email:
//   .string()            -> deve essere una stringa
//   .min(1, ...)         -> non puo' essere vuota (altrimenti "Email is required")
//   .email(...)          -> deve avere il formato di una email valida (es. a@b.com)
// Se una di queste fallisce, Zod restituisce il messaggio associato.
const email = z
  .string()
  .min(1, 'Email is required')
  .email('Enter a valid email address');

// Schema usato dal LOGIN: qui la password deve solo essere non vuota
// (la "vera" verifica avviene nel backend confrontando l'hash).
export const loginSchema = z.object({
  email,
  password: z.string().min(1, 'Password is required'),
});

// Schema usato dalla REGISTRAZIONE: qui sta la logica di "password corretta".
export const registerSchema = z
  .object({
    // Stessa regola email del login.
    email,
    // La password in fase di registrazione deve rispettare dei vincoli minimi:
    //   .min(8, ...)   -> almeno 8 caratteri (deve combaciare col backend!)
    //   .max(128, ...) -> tetto massimo, per evitare input assurdi
    password: z
      .string()
      .min(8, 'Password must be at least 8 characters')
      .max(128, 'Password is too long'),
    // Campo "conferma password": deve solo esistere a livello di singolo campo.
    // Il confronto vero e proprio con `password` lo facciamo nel .refine() sotto.
    confirmPassword: z.string().min(1, 'Please confirm your password'),
  })
  // .refine() = regola "trasversale" che vede TUTTO l'oggetto insieme.
  // Qui controlliamo che password e confirmPassword coincidano.
  // Se NON coincidono:
  //   - il messaggio "Passwords do not match" viene mostrato...
  //   - ...sotto il campo `confirmPassword` (grazie a `path: ['confirmPassword']`).
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  });

/* -------------------------------------------------------------------------- *
 * Session / Template / Exercise schemas (Phase 6)
 *
 * Live Session editing uses granular APIs. Draft set rows are not validated
 * as historical Sets — only a recorded row must carry the primary metric.
 * -------------------------------------------------------------------------- */

const blankToUndefined = (value) =>
  value === '' || value === null ? undefined : value;

const optionalPositiveInt = z.preprocess(
  blankToUndefined,
  z.coerce.number().int().gt(0).optional()
);

export const sessionMetaSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, 'Workout name is required')
    .max(120, 'Name must be 120 characters or fewer'),
  date: z.string().min(1, 'Date is required'),
});

export const templateNameSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, 'Template name is required')
    .max(120, 'Name must be 120 characters or fewer'),
});

export const templateExerciseSchema = z
  .object({
    exercise_id: z.coerce.number().int().positive(),
    name: z.string().optional(),
    muscle_group: z.string().nullable().optional(),
    primary_tracking_type: z.enum(['reps', 'duration', 'distance']).optional(),
    secondary_tracking_types: z.array(z.enum(['reps', 'duration', 'distance'])).optional(),
    target_sets: z.preprocess(
      blankToUndefined,
      z.coerce
        .number({ invalid_type_error: 'Required' })
        .int()
        .gt(0, 'Must be > 0')
    ),
    target_reps_min: optionalPositiveInt,
    target_reps_max: optionalPositiveInt,
    target_duration_seconds_min: optionalPositiveInt,
    target_duration_seconds_max: optionalPositiveInt,
    target_distance_meters_min: optionalPositiveInt,
    target_distance_meters_max: optionalPositiveInt,
  })
  .superRefine((value, ctx) => {
    const pairs = [
      ['target_reps_min', 'target_reps_max', 'Reps'],
      ['target_duration_seconds_min', 'target_duration_seconds_max', 'Duration'],
      ['target_distance_meters_min', 'target_distance_meters_max', 'Distance'],
    ];
    for (const [minKey, maxKey, label] of pairs) {
      const min = value[minKey];
      const max = value[maxKey];
      if (min == null && max == null) continue;
      if (min == null || max == null) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `${label} min and max must both be set`,
          path: [min == null ? minKey : maxKey],
        });
      } else if (min > max) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: 'Min must be ≤ max',
          path: [minKey],
        });
      }
    }
  });

export const templateSchema = templateNameSchema.extend({
  exercises: z.array(templateExerciseSchema).min(1, 'Add at least one exercise'),
});

export const personalExerciseSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, 'Name is required')
    .max(120, 'Name must be 120 characters or fewer'),
  primary_tracking_type: z.enum(['reps', 'duration', 'distance'], {
    required_error: 'Choose how this exercise is tracked',
  }),
  secondary_tracking_types: z
    .array(z.enum(['reps', 'duration', 'distance']))
    .optional()
    .default([]),
  muscle_group: z
    .string()
    .trim()
    .max(60)
    .optional()
    .transform((value) => (value ? value : undefined)),
});

// Kept for any leftover imports; live editor no longer submits this tree.
export const workoutSchema = sessionMetaSchema;

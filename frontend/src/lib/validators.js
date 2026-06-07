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
 * Workout schemas (Phase 5 Step 2)
 *
 * Rispecchiano il contratto del backend (backend/app/workouts/schemas.py):
 *   - workout.name : richiesto, 1..120 caratteri
 *   - workout.date : YYYY-MM-DD (qui sempre presente, default = oggi)
 *   - set.reps     : intero > 0
 *   - set.weight   : numero >= 0
 *
 * I campi `name`/`muscle_group` dentro un esercizio sono solo di supporto alla
 * UI (per mostrare l'esercizio scelto) e non vengono inviati al backend.
 * -------------------------------------------------------------------------- */

// `z.coerce.number` converte la stringa dell'input in numero. Una stringa vuota
// diventerebbe 0, quindi pre-processiamo "" -> undefined per far scattare il
// messaggio "Required" invece di un fuorviante "deve essere > 0".
const blankToUndefined = (value) =>
  value === '' || value === null ? undefined : value;

export const setSchema = z.object({
  reps: z.preprocess(
    blankToUndefined,
    z.coerce
      .number({ invalid_type_error: 'Required' })
      .int('Whole number')
      .gt(0, 'Must be > 0')
  ),
  weight: z.preprocess(
    blankToUndefined,
    z.coerce
      .number({ invalid_type_error: 'Required' })
      .min(0, 'Must be ≥ 0')
  ),
});

export const workoutExerciseSchema = z.object({
  exercise_id: z.coerce.number().int().positive(),
  // Solo per la UI, non inviati al backend.
  name: z.string().optional(),
  muscle_group: z.string().optional(),
  sets: z.array(setSchema).min(1, 'Add at least one set'),
});

export const workoutSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, 'Workout name is required')
    .max(120, 'Name must be 120 characters or fewer'),
  date: z.string().min(1, 'Date is required'),
  exercises: z.array(workoutExerciseSchema).min(1, 'Add at least one exercise'),
});

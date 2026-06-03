import { z } from 'zod';

/**
 * Shared Zod schemas for auth forms.
 * Mirrors the backend contract (see backend/app/auth/schemas.py):
 *   - register: email + password (min 8 chars)
 *   - login:    email + password (non-empty)
 */

const email = z
  .string()
  .min(1, 'Email is required')
  .email('Enter a valid email address');

export const loginSchema = z.object({
  email,
  password: z.string().min(1, 'Password is required'),
});

export const registerSchema = z
  .object({
    email,
    password: z
      .string()
      .min(8, 'Password must be at least 8 characters')
      .max(128, 'Password is too long'),
    confirmPassword: z.string().min(1, 'Please confirm your password'),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  });

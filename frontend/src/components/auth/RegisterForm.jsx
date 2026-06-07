// RegisterForm - react-hook-form + zod validation, wired to AuthContext.register.
// On success the user is registered, logged in, and routed to /home.

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate } from 'react-router-dom';
import { AlertCircle, Eye, EyeOff, Lock, Mail } from 'lucide-react';

import useAuth from '@/hooks/useAuth.js';
import { registerSchema } from '@/lib/validators.js';
import AppInput from '@/components/ui/AppInput.jsx';
import AppButton from '@/components/ui/AppButton.jsx';

export default function RegisterForm() {
  // Prendiamo la funzione `register` dal contesto di autenticazione e la
  // rinominiamo `registerUser` per non confonderla con la `register` di
  // react-hook-form (che serve a collegare gli input al form, vedi sotto).
  const { register: registerUser } = useAuth();
  const navigate = useNavigate();

  // Stato locale solo per la UI:
  //   showPassword  -> mostra/nasconde la password (occhio cliccabile)
  //   serverError   -> messaggio d'errore che arriva DAL BACKEND (es. email gia' usata)
  const [showPassword, setShowPassword] = useState(false);
  const [serverError, setServerError] = useState(null);

  // Configurazione di react-hook-form:
  //   - resolver: zodResolver(registerSchema) collega lo schema Zod al form,
  //     cosi' la validazione "email/password corretta" e' automatica.
  //   - defaultValues: i valori iniziali dei tre campi.
  // Cosa otteniamo:
  //   - register: collega un <input> a un campo (es. register('email'))
  //   - handleSubmit: esegue la validazione e, SOLO se passa, chiama onSubmit
  //   - errors: gli errori di validazione per ogni campo
  //   - isSubmitting: true mentre onSubmit e' in corso (per disabilitare il bottone)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(registerSchema),
    defaultValues: { email: '', password: '', confirmPassword: '' },
  });

  // onSubmit viene chiamata SOLO se la validazione Zod e' andata a buon fine.
  // A questo punto email/password sono gia' garantite "corrette" lato client.
  // Nota: estraiamo solo { email, password } e ignoriamo confirmPassword,
  // perche' al backend serve solo la password vera, non la sua conferma.
  const onSubmit = async ({ email, password }) => {
    setServerError(null); // azzera eventuali errori precedenti
    try {
      // Chiama AuthContext.register -> registra + fa login automatico.
      await registerUser({ email, password });
      // Se tutto ok, vai alla home. `replace: true` evita che il tasto
      // "indietro" del browser riporti alla pagina di registrazione.
      navigate('/home', { replace: true });
    } catch (err) {
      // Qui finiscono gli errori lato server (es. "Email already registered"
      // con status 409): li mostriamo nel banner rosso in cima al form.
      setServerError(err?.message || 'Unable to create your account. Please try again.');
    }
  };

  return (
    // handleSubmit(onSubmit): al submit, react-hook-form prima valida con Zod;
    // se ci sono errori popola `errors` e NON chiama onSubmit; se e' tutto ok,
    // chiama onSubmit con i valori. `noValidate` disattiva la validazione HTML
    // nativa del browser, cosi' usiamo solo la nostra (Zod) coerente ovunque.
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
      {serverError && (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3.5 py-3 text-sm text-destructive"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <span>{serverError}</span>
        </div>
      )}

      <AppInput
        label="Email"
        type="email"
        inputMode="email"
        autoComplete="email"
        placeholder="you@example.com"
        leftIcon={<Mail className="h-4 w-4" />}
        // errors.email?.message: se Zod ha bocciato l'email, qui appare il
        // messaggio (es. "Enter a valid email address") sotto al campo.
        error={errors.email?.message}
        // {...register('email')}: "aggancia" questo input al campo `email` del
        // form (gestisce value, onChange, onBlur, ref) senza scriverli a mano.
        {...register('email')}
      />

      <AppInput
        label="Password"
        type={showPassword ? 'text' : 'password'}
        autoComplete="new-password"
        placeholder="At least 8 characters"
        hint={!errors.password ? 'Use at least 8 characters.' : undefined}
        leftIcon={<Lock className="h-4 w-4" />}
        error={errors.password?.message}
        rightSlot={
          <button
            type="button"
            onClick={() => setShowPassword((v) => !v)}
            aria-label={showPassword ? 'Hide password' : 'Show password'}
            className="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        }
        {...register('password')}
      />

      <AppInput
        label="Confirm password"
        type={showPassword ? 'text' : 'password'}
        autoComplete="new-password"
        placeholder="Re-enter your password"
        leftIcon={<Lock className="h-4 w-4" />}
        error={errors.confirmPassword?.message}
        {...register('confirmPassword')}
      />

      <AppButton type="submit" block size="lg" loading={isSubmitting} className="mt-2">
        {isSubmitting ? 'Creating account…' : 'Create account'}
      </AppButton>
    </form>
  );
}

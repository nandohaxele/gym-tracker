// Chiamate API di autenticazione.
// Endpoint (api_contract.md): POST /auth/register, POST /auth/login, GET /auth/me
//
// `client` e' l'istanza axios condivisa (axiosClient.js). Grazie ai suoi
// interceptor, queste funzioni restituiscono GIA' il contenuto di `data`
// (non l'intera risposta { success, data, error }) e, in caso di errore,
// lanciano un Error con il messaggio del backend. Per questo qui basta un
// return one-liner: la logica comune e' centralizzata nel client.

import client from './axiosClient.js';

// Crea un nuovo account. Risolve con l'utente creato (id, email, created_at).
// Se l'email esiste gia', il backend risponde 409 e questa promise va in reject.
export async function register({ email, password }) {
  return client.post('/auth/register', { email, password });
}

// Autentica e ottiene il token. Risolve con { access_token, token_type }.
export async function login({ email, password }) {
  return client.post('/auth/login', { email, password });
}

// Restituisce l'utente attualmente autenticato (richiede header Bearer valido).
export async function me() {
  return client.get('/auth/me');
}

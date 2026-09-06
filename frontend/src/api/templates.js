// Templates API. Globals are immutable; personal templates are owner-only.

import client from './axiosClient.js';

export async function listTemplates() {
  return client.get('/templates');
}

export async function getTemplate(id) {
  return client.get(`/templates/${id}`);
}

export async function createTemplate(payload) {
  return client.post('/templates', payload);
}

export async function updateTemplate(id, payload) {
  return client.patch(`/templates/${id}`, payload);
}

export async function deleteTemplate(id) {
  return client.delete(`/templates/${id}`);
}

export async function personalizeTemplate(id, name) {
  const body = name ? { name } : undefined;
  return client.post(`/templates/${id}/personalize`, body);
}

export async function startTemplate(id) {
  return client.post(`/templates/${id}/start`);
}

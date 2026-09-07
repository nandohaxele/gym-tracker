import client from './axiosClient.js';

export async function interpretAssistant(payload) {
  return client.post('/assistant/interpret', payload);
}

export async function executeAssistant(commands) {
  return client.post('/assistant/execute', { commands });
}

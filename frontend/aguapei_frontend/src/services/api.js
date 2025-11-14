import axios from 'axios';
import { toast } from 'react-toastify';

const apiClient = axios.create({
  baseURL: 'http://127.0.0.1:8000/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => {
    if (response.status === 204) {
      return null;
    }

    const payload = response.data;
    if (payload?.success === false) {
      const apiError = payload.error || {};
      toast.error(apiError.message || 'Operacao nao pode ser concluida.');
      return Promise.reject(payload);
    }

    if (payload?.success === true) {
      return payload.data ?? null;
    }

    return payload;
  },
  (error) => {
    if (error.response) {
      const payload = error.response.data;
      if (error.response.status === 401 && error.config?.url !== '/login/') {
        toast.error('Sua sessao expirou. Por favor, faca login novamente.');
        localStorage.removeItem('authToken');
        window.location.href = '/login';
        return Promise.reject(payload);
      }

      const apiError = payload?.error || {};
      toast.error(apiError.message || payload?.message || 'Falha ao processar a requisicao.');
      return Promise.reject(
        payload || {
          success: false,
          error: { code: 'ERRO_INTERNO', message: 'Falha ao processar a requisicao.' },
        }
      );
    }

    if (error.request) {
      toast.error('Nao foi possivel conectar ao servidor.');
      return Promise.reject({
        success: false,
        error: { code: 'NETWORK_ERROR', message: 'Nao foi possivel conectar ao servidor.' },
      });
    }

    toast.error('Erro inesperado na aplicacao.');
    return Promise.reject({
      success: false,
      error: { code: 'ERRO_INTERNO', message: 'Erro inesperado na aplicacao.' },
    });
  }
);

// --- AUTENTICACAO E PERFIL ---
export const login = (email, senha) => apiClient.post('/login/', { email, senha });
export const fetchUsuarioPerfil = () => apiClient.get('/perfil/');
export const updateUsuarioPerfil = (perfilData) => apiClient.put('/perfil/', perfilData);

// --- GESTAO (BI) ---
export const fetchIndicadoresGestao = (ano) => apiClient.get('/gestao/indicadores/', { params: { ano } });
export const fetchReservasPendentesGestao = () => apiClient.get('/gestao/reservas-pendentes/');

// --- AGENDA E RESERVAS ---
export const fetchAgendaReservas = () => apiClient.get('/agenda/');
export const fetchReservaDetalhes = (reservaQuartoId) => apiClient.get(`/agenda/detalhes/${reservaQuartoId}/`);
export const createReserva = (payload) => apiClient.post('/reservas/create/', payload);
export const updateReservaCompleta = (reservaQuartoId, payload) =>
  apiClient.put(`/agenda/editar/${reservaQuartoId}/`, payload);
export const updateReservaStatus = (reservaQuartoId, payload) =>
  apiClient.patch(`/agenda/update-status/${reservaQuartoId}/`, payload);

// --- HOSPEDES (CRUD) ---
export const fetchHospedes = (status = 'Ativo', page = 1, limit = 10) =>
  apiClient.get('/hospedes/', { params: { status, page, limit } });
export const createHospede = (hospedeData) => apiClient.post('/hospedes/', hospedeData);
export const updateHospede = (hospedeId, hospedeData) => apiClient.put(`/hospedes/${hospedeId}/`, hospedeData);
export const deleteHospede = (hospedeId) => apiClient.delete(`/hospedes/${hospedeId}/`);
export const updateHospedeStatus = (hospedeId, novoStatus) =>
  apiClient.patch(`/hospedes/${hospedeId}/`, { ativo: novoStatus });

// --- QUARTOS (CRUD) ---
export const fetchQuartos = (status = 'Disponivel') => apiClient.get('/quartos/', { params: { status } });
export const fetchQuartoDetalhes = (quartoId) => apiClient.get(`/quartos/${quartoId}/`);
export const createQuarto = (quartoData) => apiClient.post('/quartos/', quartoData);
export const updateQuarto = (quartoId, quartoData) => apiClient.put(`/quartos/${quartoId}/`, quartoData);
export const deleteQuarto = (quartoId) => apiClient.delete(`/quartos/${quartoId}/`);

export default apiClient;

import axios from 'axios';
import { toast } from 'react-toastify'; 

// ... (Configuração do apiClient e interceptor de REQUISIÇÃO mantidos) ...
const apiClient = axios.create({
  baseURL: 'http://127.0.0.1:8000/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  }
});

apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);


// =======================================================================
// 3. 🎓 INTERCEPTADOR DE RESPOSTA (CORRIGIDO)
// =======================================================================
apiClient.interceptors.response.use(
    (response) => {
        // --- SUCESSO (Status 2xx) ---
        
        if (response.status === 204) {
            return null; 
        }

        // 🎓 CORREÇÃO: A exceção para '/login/' foi removida.
        //
        // Agora, TODAS as respostas de sucesso (incluindo o login)
        // passarão por esta linha.
        // O interceptor sempre retornará o conteúdo da chave "data".
        //
        // Backend: { status: 'ok', data: { token: '...' } }
        // Componente: { token: '...' }
        //
        return response.data.data;
    },
    (error) => {
        // --- ERRO (Status 4xx, 5xx ou Rede) ---
        
        if (error.response) {
            const data = error.response.data; 
            const status = error.response.status;

            // Erro Global: 401 (Não Autorizado / Token Expirado)
            if (status === 401) {
                // 🎓 ATENÇÃO: Se a URL *NÃO FOR* a de login, redireciona.
                //    (Evita loop de redirect se o próprio login falhar com 401)
                if (error.config.url !== '/login/') {
                    toast.error('Sua sessão expirou. Por favor, faça login novamente.');
                    localStorage.removeItem('authToken');
                    window.location.href = '/login';
                    return;
                }
            }
            
            // ... (O resto do tratamento de erro 500, 409, 400 está correto) ...
            if (status === 500) {
                toast.error(data.message || 'Erro interno no servidor. Contate o administrador.');
            }
            if (status === 409) {
                 toast.warn(data.message || 'Conflito de dados detectado.');
            }
            
            // Rejeita a promessa com o OBJETO DE ERRO (data)
            return Promise.reject(data);

        } else if (error.request) {
            toast.error('Não foi possível conectar ao servidor.');
            return Promise.reject({ code: 'NETWORK_ERROR', message: 'Não foi possível conectar ao servidor.' });
        }

        toast.error('Erro inesperado na aplicação.');
        return Promise.reject(error);
    }
);


// =======================================================================
// 4. FUNÇÕES DE API (Estão corretas e não precisam de mudança)
// =======================================================================
// (login, fetchUsuarioPerfil, fetchIndicadoresGestao, fetchAgendaReservas, etc...)
// --- AUTENTICAÇÃO E PERFIL ---
export const login = (email, senha) => {
    return apiClient.post('/login/', { email, senha });
};
export const fetchUsuarioPerfil = () => {
    return apiClient.get('/perfil/');
};
export const updateUsuarioPerfil = (perfilData) => {
    return apiClient.put('/perfil/', perfilData);
};

// --- GESTÃO (BI) ---
export const fetchIndicadoresGestao = (ano) => {
    return apiClient.get('/gestao/indicadores/', { params: { ano } });
};

// --- AGENDA E RESERVAS ---
export const fetchAgendaReservas = () => {
    return apiClient.get('/agenda/');
};
export const fetchReservaDetalhes = (reservaQuartoId) => {
    return apiClient.get(`/agenda/detalhes/${reservaQuartoId}/`);
};
export const createReserva = (payload) => {
    // 🎓 ATENÇÃO: Seu 'urls.py' mapeia 'reservas/create/' para o POST
    return apiClient.post('/reservas/create/', payload); 
};
export const updateReservaCompleta = (reservaQuartoId, payload) => {
    return apiClient.put(`/agenda/editar/${reservaQuartoId}/`, payload);
};
export const updateReservaStatus = (reservaQuartoId, payload) => {
    return apiClient.patch(`/agenda/update-status/${reservaQuartoId}/`, payload);
};

// --- HÓSPEDES (CRUD) ---
export const fetchHospedes = (status = 'Ativo', page = 1, limit = 10) => {
    // Passa o status como um parâmetro de query
    return apiClient.get('/hospedes/', { params: { status, page, limit } });
};
export const createHospede = (hospedeData) => {
    return apiClient.post('/hospedes/', hospedeData);
};
export const updateHospede = (hospedeId, hospedeData) => {
    return apiClient.put(`/hospedes/${hospedeId}/`, hospedeData);
};
export const deleteHospede = (hospedeId) => {
    return apiClient.delete(`/hospedes/${hospedeId}/`);
};
export const updateHospedeStatus = (hospedeId, novoStatus) => {
    return apiClient.patch(`/hospedes/${hospedeId}/`, { ativo: novoStatus });
};

// --- QUARTOS (CRUD) ---
export const fetchQuartos = (status = 'Disponível') => {
    // Passa o status como um parâmetro de query
    return apiClient.get('/quartos/', { params: { status } });
};
export const fetchQuartoDetalhes = (quartoId) => {
    return apiClient.get(`/quartos/${quartoId}/`);
};
export const createQuarto = (quartoData) => {
    return apiClient.post('/quartos/', quartoData);
};
export const updateQuarto = (quartoId, quartoData) => {
    return apiClient.put(`/quartos/${quartoId}/`, quartoData);
};
export const deleteQuarto = (quartoId) => {
    // (Esta função já existe e será usada para o "Excluir")
    return apiClient.delete(`/quartos/${quartoId}/`);
};

// =======================================================================
// 5. EXPORTAÇÃO PADRÃO (DEFAULT)
// =======================================================================
export default apiClient;
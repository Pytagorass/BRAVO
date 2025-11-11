import axios from 'axios';

// =======================================================================
// 1. CONFIGURAÇÃO DO AXIOS (O 'apiClient')
// =======================================================================
// Configura a URL base da sua API do Django.
const apiClient = axios.create({
  baseURL: 'http://127.0.0.1:8000/api', // A URL do seu back-end
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  }
});

// =======================================================================
// 2. 🎓 INTERCEPTADOR DE REQUISIÇÃO (Segurança JWT)
// =======================================================================
// Este é o "guardião" que anexa o token em todas as chamadas.
apiClient.interceptors.request.use(
    (config) => {
        // 1. Pega o token do localStorage (que salvamos no Login.js)
        const token = localStorage.getItem('authToken');
        
        // 2. Se o token existir, anexa ele no cabeçalho 'Authorization'
        if (token) {
            // O formato 'Bearer' é o padrão para JWT
            config.headers['Authorization'] = `Bearer ${token}`;
        }
        
        // 3. Deixa a requisição continuar
        return config;
    },
    (error) => {
        // Em caso de erro ao preparar a requisição
        return Promise.reject(error);
    }
);

// =======================================================================
// 2. FUNÇÕES DE API (EXPORTAÇÕES NOMEADAS)
// =======================================================================

/**
 * Busca os dados de reservas para o gráfico de Gantt.
 * Usado em: AgendaDashboard.js
 */
export const fetchAgendaReservas = () => {
  // Faz a chamada GET para /api/agenda/
  const cacheBuster = `_t=${new Date().getTime()}`;
    return apiClient.get(`/agenda/?${cacheBuster}`);
};

/**
 * Autentica um usuário.
 * Usado em: Login.js
 * (Placeholder - A lógica de back-end ainda será criada)
 */
/**
 * Autentica um usuário.
 * Faz um POST real para o nosso endpoint /api/login/ customizado.
 */
export const login = (email, senha) => {
    // Usamos 'email_usuario' e 'senha' se o backend esperar,
    // mas nossa view espera 'email' e 'senha'.
    return apiClient.post('/login/', { email, senha });
};

/**
 * Busca a lista completa de clientes (hóspedes).
 * Usado em: ClientesPage.js
 */
// export const fetchClientes = () => {
//     return apiClient.get('/clientes/');
// };
export const fetchHospedes = () => {
    // Atualizado de /clientes/ para /hospedes/
    return apiClient.get('/hospedes/');
};

export const fetchQuartos = () => {
  // Faz a chamada GET para /api/quartos/
  return apiClient.get('/quartos/');
};
/**
 * Busca os KPIs e dados de faturamento para o Dashboard de Gestão.
 * Usado em: GestaoPage.js
 */
export const fetchIndicadoresGestao = () => {
    return apiClient.get('/gestao/indicadores/');
};

export const fetchUsuarioPerfil = () => {
    return apiClient.get('/perfil/');
};

/**
 * Atualiza os dados do perfil do usuário logado.
 * Usado em: UsuarioModal.js
 */
export const updateUsuarioPerfil = (perfilData) => {
    // perfilData = { nome_usuario, email_usuario, senha (opcional) }
    return apiClient.put('/perfil/', perfilData);
};

// FUNÇÃO DE EDIÇÃO COMPLETA
/**
 * PUT: Atualiza uma reserva existente (Formulário completo)
 * @param {number} reservaQuartoId - O ID da (tabela reserva_quarto)
 * @param {object} payload - O objeto completo da reserva (do formulário)
 */
export const updateReservaCompleta = (reservaQuartoId, payload) => {
    return apiClient.put(`/agenda/editar/${reservaQuartoId}/`, payload);
};

// =======================================================================
// 3. EXPORTAÇÃO PADRÃO (DEFAULT)
// =======================================================================

/**
 * Exporta a instância 'apiClient' como padrão.
 * Isso corrige o erro 'does not contain a default export'.
 * Permite que outros componentes façam chamadas diretas, ex:
 * import apiClient from './api';
 * apiClient.post('/clientes/', dados);
 */
export default apiClient;
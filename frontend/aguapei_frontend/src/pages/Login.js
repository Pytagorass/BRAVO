import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Container, Form, Button, Alert, Card } from 'react-bootstrap';
import { login } from '../services/api';
import './Login.css';

function Login() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    // ==========================================================
    // 🎓 handleSubmit CORRIGIDO
    // ==========================================================
    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            // 1. CAPTURAMOS a resposta da nossa API de login
            const response = await login(email, password);

            // 2. VERIFICAMOS se o token veio na resposta
            if (response.data && response.data.token) {
                
                // 3. SALVAMOS O TOKEN no localStorage
                // O localStorage é um "depósito" do navegador que persiste
                // mesmo se o usuário fechar a aba. É aqui que guardamos
                // a "chave" de autenticação (o JWT).
                localStorage.setItem('authToken', response.data.token);
                
                // 4. SALVAMOS OS DADOS DO USUÁRIO
                // Também guardamos os dados do usuário (em formato JSON)
                // para que o Sidebar possa mostrar o nome dele.
                localStorage.setItem('usuario', JSON.stringify(response.data.usuario));

                // 5. REDIRECIONAMOS (somente após salvar o token)
                navigate('/agenda');
            } else {
                // Caso a API não retorne um token (erro inesperado)
                setError('Resposta de login inválida do servidor.');
            }

        } catch (err) {
            // 6. TRATAMENTO DE ERRO MELHORADO
            // Em vez de 'err.message' (genérico), nós lemos a
            // resposta 'erro' que o nosso back-end Django enviou.
            if (err.response && err.response.data && err.response.data.erro) {
                setError(err.response.data.erro);
            } else {
                // Erro de rede (ex: servidor Django desligado)
                setError('Não foi possível conectar ao servidor.');
            }
        } finally {
            setLoading(false);
        }
    };
    // ==========================================================
    // FIM DA CORREÇÃO
    // ==========================================================


    return (
        <div className="login-background">
            <Container className="d-flex justify-content-center align-items-center vh-100">
                <Card className="login-card p-4 shadow-sm">
                    <Card.Body>
                        <h3 className="text-center fw-bold" style={{ color: '#26522c' }}>
                            Pathfinder
                        </h3>
                        <p className="text-center text-muted mb-4">Aguapé</p>

                        <Form onSubmit={handleSubmit}>
                            {error && <Alert variant="danger">{error}</Alert>}

                            <Form.Group className="mb-3" controlId="formBasicEmail">
                                <Form.Label>E-mail</Form.Label>
                                <Form.Control
                                    type="email"
                                    placeholder="Digite seu e-mail"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    required
                                />
                            </Form.Group>

                            <Form.Group className="mb-3" controlId="formBasicPassword">
                                <Form.Label>Senha</Form.Label>
                                <Form.Control
                                    type="password"
                                    placeholder="Senha"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    required
                                />
                            </Form.Group>

                            <div className="d-grid gap-2 mt-4">
                                <Button className="btn-entrar" type="submit" disabled={loading}>
                                    {loading ? 'Entrando...' : 'Entrar'}
                                </Button>
                                
                                <Button variant="danger" type="button">
                                    Esqueci a Senha
                                </Button>
                            </div>
                        </Form>
                    </Card.Body>
                </Card>
            </Container>
        </div>
    );
}

export default Login;
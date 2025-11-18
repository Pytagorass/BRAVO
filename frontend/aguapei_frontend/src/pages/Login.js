import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Container, Form, Button, Alert, Card } from 'react-bootstrap';
// 🎓 Importamos a função 'login' do nosso api.js refatorado
import { login } from '../services/api';
import './Login.css';

function Login() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    // ==========================================================
    // 🎓 handleSubmit REFATORADO (Alinhado com api.js e views.py)
    // ==========================================================
    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            // 1. CHAMA A API
            // Graças ao interceptor do 'api.js', 'responseData'
            // já será o objeto 'data' retornado pelo 'views.py'.
            // responseData = { token: "...", usuario: { ... } }
            const responseData = await login(email, password);

            // 2. VERIFICA O SUCESSO
            // (Não precisamos mais de 'response.data.token')
            if (responseData.token) {
                
                // 3. SALVA O TOKEN
                localStorage.setItem('authToken', responseData.token);
                
                // 4. SALVA OS DADOS DO USUÁRIO
                localStorage.setItem('usuario', JSON.stringify(responseData.usuario));

                // 5. REDIRECIONA
                navigate('/agenda'); // Redireciona para o dashboard principal
            } else {
                // Caso a API não retorne um token (erro inesperado)
                setError('Resposta de login inválida do servidor.');
            }

        } catch (err) {
            // 6. 🎓 TRATAMENTO DE ERRO PADRONIZADO
            // Graças ao interceptor, 'err' já é o nosso objeto JSON de erro
            // err = { status: 'error', code: '...', message: '...' }
            
            if (err.message) {
                // Ex: "Credenciais inválidas" (Erro 401)
                // Ex: "Erro interno: ..." (Erro 500)
                setError(err.message);
            } else {
                // Erro de rede (ex: servidor Django desligado)
                // (O interceptor já deve ter mostrado um toast, mas temos um fallback)
                setError('Não foi possível conectar ao servidor.');
            }
        } finally {
            setLoading(false);
        }
    };
    // ==========================================================
    // FIM DA REFATORAÇÃO
    // ==========================================================


    return (
        <div className="login-background">
            <Container className="d-flex justify-content-center align-items-center vh-100">
                <Card className="login-card p-4 shadow-sm">
                    <Card.Body className="text-center">
                        <h3 className="text-center fw-bold" style={{ color: '#26522c' }}>
                            Aguapé
                        </h3>
                        <img
                            src='/iconeAguape.ico'
                            alt='Logo Aguapé'
                            className="login-logo"
                        />
                        <p className="text-center text-muted mb-4">Grupo Pathfinder</p>

                        <Form onSubmit={handleSubmit}>
                            
                            {/* 🎓 Este Alert agora exibirá as mensagens corretas da API */}
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
                                <Button className="btn-entrar" type="submit" disabled={loading} style={{ backgroundColor: '#26522c', borderColor: '#26522c' }}>
                                    {loading ? 'Entrando...' : 'Entrar'}
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
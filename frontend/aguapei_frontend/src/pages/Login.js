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
    // handleSubmit
    // ==========================================================
    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            // 1. CHAMA A API
            const responseData = await login(email, password);

            // 2. VERIFICA O SUCESSO
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
            // 6. TRATAMENTO DE ERRO PADRONIZADO
            
            console.error('Erro ao efetuar login:', err);
            setError('Usuário ou Senha inválidos. Tente novamente.');
        } finally {
            setLoading(false);
        }
    };

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

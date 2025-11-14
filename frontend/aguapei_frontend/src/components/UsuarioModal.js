import React, { useState, useEffect } from 'react';
import { Modal, Button, Form, Alert, Spinner } from 'react-bootstrap';
import { fetchUsuarioPerfil, updateUsuarioPerfil } from '../services/api';
import { toast } from 'react-toastify';

function UsuarioModal({ show, handleClose }) {
  const [formData, setFormData] = useState({
    nome_usuario: '',
    email_usuario: '',
    senha: '',
    confirmar_senha: ''
  });

  const [loading, setLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    if (show) {
      const loadProfile = async () => {
        setLoading(true);
        setError(null);
        setSuccess(null);

        try {
          const perfilData = await fetchUsuarioPerfil();
          setFormData({
            nome_usuario: perfilData.nome_usuario,
            email_usuario: perfilData.email_usuario,
            senha: '',
            confirmar_senha: ''
          });
        } catch (err) {
          const apiError = err?.error || err || {};
          setError(apiError.message || 'Falha ao carregar dados do perfil.');
        } finally {
          setLoading(false);
        }
      };

      loadProfile();
    }
  }, [show]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (formData.senha !== formData.confirmar_senha) {
      setError('As novas senhas não coincidem.');
      return;
    }

    setIsSaving(true);

    const payload = {
      nome_usuario: formData.nome_usuario,
      email_usuario: formData.email_usuario
    };

    if (formData.senha) {
      payload.senha = formData.senha;
    }

    try {
      await updateUsuarioPerfil(payload);
      setSuccess('Perfil atualizado com sucesso!');
      toast.success('Perfil atualizado!');

      const usuarioLocal = JSON.parse(localStorage.getItem('usuario'));
      if (
        usuarioLocal &&
        (usuarioLocal.nome !== payload.nome_usuario ||
          usuarioLocal.email !== payload.email_usuario)
      ) {
        usuarioLocal.nome = payload.nome_usuario;
        usuarioLocal.email = payload.email_usuario;
        localStorage.setItem('usuario', JSON.stringify(usuarioLocal));
      }

      setTimeout(handleClose, 2000);
    } catch (errorData) {
      console.error('Erro ao atualizar perfil:', errorData);

      const apiError = errorData?.error || errorData || {};
      if (apiError.code === 'CONFLICT') {
        setError(apiError.message);
      } else if (apiError.message) {
        setError(apiError.message);
      } else {
        setError('Erro ao atualizar o perfil.');
      }
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Modal show={show} onHide={handleClose} backdrop="static">
      <Modal.Header closeButton>
        <Modal.Title style={{ color: '#26522c' }}>Editar Perfil</Modal.Title>
      </Modal.Header>

      <Form onSubmit={handleSubmit}>
        <Modal.Body>
          {loading && (
            <div className="text-center">
              <Spinner animation="border" />
            </div>
          )}

          {error && <Alert variant="danger">{error}</Alert>}
          {success && <Alert variant="success">{success}</Alert>}

          {!loading && (
            <>
              <Form.Group className="mb-3" controlId="nome_usuario">
                <Form.Label>Nome</Form.Label>
                <Form.Control
                  type="text"
                  name="nome_usuario"
                  value={formData.nome_usuario}
                  onChange={handleChange}
                  required
                />
              </Form.Group>

              <Form.Group className="mb-3" controlId="email_usuario">
                <Form.Label>E-mail</Form.Label>
                <Form.Control
                  type="email"
                  name="email_usuario"
                  value={formData.email_usuario}
                  onChange={handleChange}
                  required
                />
              </Form.Group>

              <hr />
              <p className="text-muted">
                Deixe em branco para não alterar a senha.
              </p>

              <Form.Group className="mb-3" controlId="senha">
                <Form.Label>Nova Senha</Form.Label>
                <Form.Control
                  type="password"
                  name="senha"
                  value={formData.senha}
                  onChange={handleChange}
                />
              </Form.Group>

              <Form.Group className="mb-3" controlId="confirmar_senha">
                <Form.Label>Confirmar Nova Senha</Form.Label>
                <Form.Control
                  type="password"
                  name="confirmar_senha"
                  value={formData.confirmar_senha}
                  onChange={handleChange}
                />
              </Form.Group>
            </>
          )}
        </Modal.Body>

        <Modal.Footer>
          <Button variant="secondary" onClick={handleClose} disabled={isSaving}>
            Cancelar
          </Button>
          <Button
            variant="success"
            type="submit"
            disabled={isSaving || loading}
            style={{ backgroundColor: '#26522c' }}
          >
            {isSaving ? (
              <Spinner as="span" animation="border" size="sm" />
            ) : (
              'Salvar Alterações'
            )}
          </Button>
        </Modal.Footer>
      </Form>
    </Modal>
  );
}

export default UsuarioModal;

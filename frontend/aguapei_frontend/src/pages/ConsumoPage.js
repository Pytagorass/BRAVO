import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Alert, Button, ButtonGroup, Form, Spinner } from 'react-bootstrap';
import { Edit2, Plus, Power, Save, Tag, X } from 'react-feather';
import { toast } from 'react-toastify';

import {
  createConsumoCategoria,
  createConsumoProduto,
  fetchConsumoCategorias,
  fetchConsumoProdutos,
  updateConsumoProduto,
  updateConsumoProdutoStatus,
} from '../services/api';
import './ConsumoPage.css';

const ORIGENS = ['Restaurante', 'Lojinha'];
const ORIGENS_CATEGORIA = ['Lojinha'];

const produtoInicial = {
  tipo_categoria: 'Restaurante',
  fk_categoria: '',
  nome_produto: '',
  descricao: '',
  preco_atual: '',
  controla_estoque: false,
  estoque_atual: 0,
  estoque_minimo: 0,
  ativo: 'Ativo',
};

const categoriaInicial = {
  nome_categoria: '',
  tipo_categoria: 'Lojinha',
};

const formatMoney = (value) =>
  Number(value || 0).toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  });

const formatOrigemConsumo = (origem) => (origem === 'Restaurante' ? 'Bebidas' : origem);

const ConsumoPage = () => {
  const [produtos, setProdutos] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [origemFiltro, setOrigemFiltro] = useState('Todos');
  const [ativoFiltro, setAtivoFiltro] = useState('Ativo');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const [produtoForm, setProdutoForm] = useState(produtoInicial);
  const [produtoEditando, setProdutoEditando] = useState(null);
  const [categoriaForm, setCategoriaForm] = useState(categoriaInicial);
  const [savingCategoria, setSavingCategoria] = useState(false);

  const carregarDados = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const produtoParams = {};
      if (origemFiltro !== 'Todos') produtoParams.origem = origemFiltro;
      if (ativoFiltro !== 'Todos') produtoParams.ativo = ativoFiltro;

      const [categoriasData, produtosData] = await Promise.all([
        fetchConsumoCategorias({ ativo: 'Todos' }),
        fetchConsumoProdutos(produtoParams),
      ]);

      setCategorias(categoriasData || []);
      setProdutos(produtosData || []);
    } catch (err) {
      const apiError = err?.error || err || {};
      setError(apiError.message || 'Falha ao carregar produtos de consumo.');
    } finally {
      setLoading(false);
    }
  }, [ativoFiltro, origemFiltro]);

  useEffect(() => {
    carregarDados();
  }, [carregarDados]);

  const categoriasDoProduto = useMemo(
    () =>
      categorias.filter(
        (categoria) =>
          categoria.tipo_categoria === produtoForm.tipo_categoria &&
          categoria.ativo === 'Ativo'
      ),
    [categorias, produtoForm.tipo_categoria]
  );

  const resumo = useMemo(() => {
    const ativos = produtos.filter((produto) => produto.ativo === 'Ativo').length;
    const bebidas = produtos.filter((produto) => produto.tipo_categoria === 'Restaurante').length;
    const estoqueBaixo = produtos.filter(
      (produto) =>
        produto.controla_estoque &&
        Number(produto.estoque_atual || 0) <= Number(produto.estoque_minimo || 0)
    ).length;

    return { ativos, bebidas, estoqueBaixo };
  }, [produtos]);

  const limparProdutoForm = () => {
    setProdutoEditando(null);
    setProdutoForm(produtoInicial);
  };

  const handleProdutoChange = (field, value) => {
    setProdutoForm((prev) => {
      const next = { ...prev, [field]: value };
      if (field === 'tipo_categoria') {
        next.fk_categoria = '';
      }
      if (field === 'controla_estoque' && !value) {
        next.estoque_atual = 0;
        next.estoque_minimo = 0;
      }
      return next;
    });
  };

  const handleEditarProduto = (produto) => {
    setProdutoEditando(produto);
    setProdutoForm({
      tipo_categoria: produto.tipo_categoria,
      fk_categoria: produto.fk_categoria,
      nome_produto: produto.nome_produto || '',
      descricao: produto.descricao || '',
      preco_atual: produto.preco_atual ?? '',
      controla_estoque: Boolean(produto.controla_estoque),
      estoque_atual: produto.estoque_atual || 0,
      estoque_minimo: produto.estoque_minimo || 0,
      ativo: produto.ativo || 'Ativo',
    });
  };

  const handleSubmitProduto = async (event) => {
    event.preventDefault();

    if (!produtoForm.fk_categoria) {
      toast.error('Selecione uma categoria para o produto.');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        ...produtoForm,
        fk_categoria: Number(produtoForm.fk_categoria),
        preco_atual: Number(produtoForm.preco_atual || 0),
        estoque_atual: Number(produtoForm.estoque_atual || 0),
        estoque_minimo: Number(produtoForm.estoque_minimo || 0),
      };

      if (produtoEditando) {
        await updateConsumoProduto(produtoEditando.id_produto, payload);
        toast.success('Produto atualizado.');
      } else {
        await createConsumoProduto(payload);
        toast.success('Produto cadastrado.');
      }

      limparProdutoForm();
      await carregarDados();
    } catch (err) {
      const apiError = err?.error || err || {};
      toast.error(apiError.message || 'Falha ao salvar produto.');
    } finally {
      setSaving(false);
    }
  };

  const handleToggleProduto = async (produto) => {
    const novoStatus = produto.ativo === 'Ativo' ? 'Inativo' : 'Ativo';
    try {
      await updateConsumoProdutoStatus(produto.id_produto, novoStatus);
      toast.success(`Produto marcado como ${novoStatus}.`);
      await carregarDados();
    } catch (err) {
      const apiError = err?.error || err || {};
      toast.error(apiError.message || 'Falha ao alterar status do produto.');
    }
  };

  const handleSubmitCategoria = async (event) => {
    event.preventDefault();
    if (!categoriaForm.nome_categoria.trim()) {
      toast.error('Informe o nome da categoria.');
      return;
    }

    setSavingCategoria(true);
    try {
      await createConsumoCategoria(categoriaForm);
      toast.success('Categoria criada.');
      setCategoriaForm(categoriaInicial);
      await carregarDados();
    } catch (err) {
      const apiError = err?.error || err || {};
      toast.error(apiError.message || 'Falha ao criar categoria.');
    } finally {
      setSavingCategoria(false);
    }
  };

  const renderTabela = () => {
    if (loading && produtos.length === 0) {
      return (
        <div className="consumo-loading">
          <Spinner animation="border" variant="success" />
          <p>Carregando produtos...</p>
        </div>
      );
    }

    if (error) {
      return (
        <Alert variant="danger">
          <Alert.Heading>Erro ao Carregar Consumo</Alert.Heading>
          <p>{error}</p>
          <Button onClick={carregarDados} variant="danger">
            Tentar Novamente
          </Button>
        </Alert>
      );
    }

    if (!loading && produtos.length === 0) {
      return <div className="consumo-empty">Nenhum produto encontrado para este filtro.</div>;
    }

    return (
      <div className="consumo-table-shell">
        <div className="table-responsive">
          <table className="table table-hover align-middle app-data-table">
            <thead>
              <tr>
                <th>Produto</th>
                <th>Origem</th>
                <th>Preco</th>
                <th>Estoque</th>
                <th>Status</th>
                <th style={{ width: '180px' }}>Acoes</th>
              </tr>
            </thead>
            <tbody>
              {produtos.map((produto) => (
                <tr key={produto.id_produto}>
                  <td>
                    <span className="consumo-product-name">{produto.nome_produto}</span>
                    {produto.descricao && (
                      <span className="consumo-product-desc">{produto.descricao}</span>
                    )}
                  </td>
                  <td>
                    <span className={`consumo-origin-pill ${produto.tipo_categoria.toLowerCase()}`}>
                      {formatOrigemConsumo(produto.tipo_categoria)}
                    </span>
                    <span className="consumo-category-text">{produto.nome_categoria}</span>
                  </td>
                  <td>
                    <strong>{formatMoney(produto.preco_atual)}</strong>
                  </td>
                  <td>
                    {produto.controla_estoque ? (
                      <span className="consumo-stock-pill">
                        {produto.estoque_atual} un.
                        {Number(produto.estoque_atual) <= Number(produto.estoque_minimo) && (
                          <span className="consumo-stock-alert">baixo</span>
                        )}
                      </span>
                    ) : (
                      <span className="table-soft-pill">Livre</span>
                    )}
                  </td>
                  <td>
                    <span className={`consumo-status-pill ${produto.ativo === 'Ativo' ? 'active' : 'inactive'}`}>
                      {produto.ativo}
                    </span>
                  </td>
                  <td>
                    <div className="table-action-group">
                      <Button
                        size="sm"
                        variant="outline-secondary"
                        onClick={() => handleEditarProduto(produto)}
                      >
                        <Edit2 size={14} />
                        Editar
                      </Button>
                      <Button
                        size="sm"
                        variant={produto.ativo === 'Ativo' ? 'outline-danger' : 'outline-success'}
                        onClick={() => handleToggleProduto(produto)}
                      >
                        <Power size={14} />
                        {produto.ativo === 'Ativo' ? 'Inativar' : 'Ativar'}
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  return (
    <div className="consumo-page">
      <div className="page-header">
        <div className="page-title-block">
          <h1>Gestao de Consumo</h1>
          <span className="page-title-meta">Produtos, precos e estoque para bebidas e lojinha</span>
        </div>

        <div className="consumo-toolbar">
          <ButtonGroup>
            {['Todos', ...ORIGENS].map((origem) => (
              <Button
                key={origem}
                variant={origemFiltro === origem ? 'success' : 'outline-secondary'}
                onClick={() => setOrigemFiltro(origem)}
                style={
                  origemFiltro === origem
                    ? { backgroundColor: '#26522c', borderColor: '#26522c' }
                    : {}
                }
              >
                {formatOrigemConsumo(origem)}
              </Button>
            ))}
          </ButtonGroup>

          <ButtonGroup>
            {['Ativo', 'Inativo', 'Todos'].map((status) => (
              <Button
                key={status}
                variant={ativoFiltro === status ? 'success' : 'outline-secondary'}
                onClick={() => setAtivoFiltro(status)}
                style={
                  ativoFiltro === status
                    ? { backgroundColor: '#26522c', borderColor: '#26522c' }
                    : {}
                }
              >
                {status}
              </Button>
            ))}
          </ButtonGroup>
        </div>
      </div>

      <div className="page-summary-grid consumo-summary-grid">
        <div className="summary-card">
          <span className="summary-label">Produtos</span>
          <strong>{produtos.length}</strong>
        </div>
        <div className="summary-card">
          <span className="summary-label">Ativos</span>
          <strong>{resumo.ativos}</strong>
        </div>
        <div className="summary-card">
          <span className="summary-label">Bebidas</span>
          <strong>{resumo.bebidas}</strong>
        </div>
        <div className="summary-card">
          <span className="summary-label">Estoque baixo</span>
          <strong>{resumo.estoqueBaixo}</strong>
        </div>
      </div>

      <div className="consumo-layout">
        <section className="consumo-form-panel">
          <div className="consumo-panel-title">
            <Plus size={18} />
            <span>{produtoEditando ? 'Editar Produto' : 'Novo Produto'}</span>
          </div>

          <Form onSubmit={handleSubmitProduto}>
            <Form.Group className="mb-3">
              <Form.Label>Origem</Form.Label>
              <Form.Select
                value={produtoForm.tipo_categoria}
                onChange={(event) => handleProdutoChange('tipo_categoria', event.target.value)}
              >
                {ORIGENS.map((origem) => (
                  <option key={origem} value={origem}>
                    {formatOrigemConsumo(origem)}
                  </option>
                ))}
              </Form.Select>
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>Categoria</Form.Label>
              <Form.Select
                value={produtoForm.fk_categoria}
                onChange={(event) => handleProdutoChange('fk_categoria', event.target.value)}
              >
                <option value="">Selecione</option>
                {categoriasDoProduto.map((categoria) => (
                  <option key={categoria.id_categoria} value={categoria.id_categoria}>
                    {categoria.nome_categoria}
                  </option>
                ))}
              </Form.Select>
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>Produto</Form.Label>
              <Form.Control
                value={produtoForm.nome_produto}
                onChange={(event) => handleProdutoChange('nome_produto', event.target.value)}
                placeholder="Ex.: Agua mineral, Camiseta Bravo"
              />
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>Descricao</Form.Label>
              <Form.Control
                as="textarea"
                rows={2}
                value={produtoForm.descricao}
                onChange={(event) => handleProdutoChange('descricao', event.target.value)}
              />
            </Form.Group>

            <div className="consumo-form-row">
              <Form.Group>
                <Form.Label>Preco</Form.Label>
                <Form.Control
                  type="number"
                  min="0"
                  step="0.01"
                  value={produtoForm.preco_atual}
                  onChange={(event) => handleProdutoChange('preco_atual', event.target.value)}
                />
              </Form.Group>

              <Form.Group>
                <Form.Label>Status</Form.Label>
                <Form.Select
                  value={produtoForm.ativo}
                  onChange={(event) => handleProdutoChange('ativo', event.target.value)}
                >
                  <option value="Ativo">Ativo</option>
                  <option value="Inativo">Inativo</option>
                </Form.Select>
              </Form.Group>
            </div>

            <Form.Check
              className="consumo-stock-toggle"
              type="checkbox"
              label="Controla estoque"
              checked={produtoForm.controla_estoque}
              onChange={(event) => handleProdutoChange('controla_estoque', event.target.checked)}
            />

            <div className="consumo-form-row">
              <Form.Group>
                <Form.Label>Estoque atual</Form.Label>
                <Form.Control
                  type="number"
                  min="0"
                  disabled={!produtoForm.controla_estoque}
                  value={produtoForm.estoque_atual}
                  onChange={(event) => handleProdutoChange('estoque_atual', event.target.value)}
                />
              </Form.Group>

              <Form.Group>
                <Form.Label>Estoque minimo</Form.Label>
                <Form.Control
                  type="number"
                  min="0"
                  disabled={!produtoForm.controla_estoque}
                  value={produtoForm.estoque_minimo}
                  onChange={(event) => handleProdutoChange('estoque_minimo', event.target.value)}
                />
              </Form.Group>
            </div>

            <div className="consumo-form-actions">
              {produtoEditando && (
                <Button variant="outline-secondary" type="button" onClick={limparProdutoForm}>
                  <X size={15} />
                  Cancelar
                </Button>
              )}
              <Button type="submit" className="page-primary-action" disabled={saving}>
                <Save size={15} />
                {saving ? 'Salvando...' : 'Salvar Produto'}
              </Button>
            </div>
          </Form>

          <div className="consumo-category-box">
            <div className="consumo-panel-title small">
              <Tag size={16} />
              <span>Nova Categoria da Lojinha</span>
            </div>
            <Form onSubmit={handleSubmitCategoria}>
              <Form.Group className="mb-2">
                <Form.Control
                  value={categoriaForm.nome_categoria}
                  onChange={(event) =>
                    setCategoriaForm((prev) => ({ ...prev, nome_categoria: event.target.value }))
                  }
                  placeholder="Ex.: Souvenirs"
                />
              </Form.Group>
              <div className="consumo-category-actions">
                <Form.Select
                  value={categoriaForm.tipo_categoria}
                  onChange={(event) =>
                    setCategoriaForm((prev) => ({ ...prev, tipo_categoria: event.target.value }))
                  }
                >
                  {ORIGENS_CATEGORIA.map((origem) => (
                    <option key={origem} value={origem}>
                      {formatOrigemConsumo(origem)}
                    </option>
                  ))}
                </Form.Select>
                <Button type="submit" variant="outline-success" disabled={savingCategoria}>
                  <Plus size={15} />
                </Button>
              </div>
            </Form>
          </div>
        </section>

        <section className="consumo-list-panel">{renderTabela()}</section>
      </div>
    </div>
  );
};

export default ConsumoPage;

-- Tabela para os Itens da Lista
CREATE TABLE IF NOT EXISTS itens_lista (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    categoria TEXT,
    comprado BOOLEAN DEFAULT FALSE,
    preco NUMERIC(10, 2),
    user_id UUID
);

-- Tabela para o Histórico de Compras Finalizadas
CREATE TABLE IF NOT EXISTS historico_compras (
    id SERIAL PRIMARY KEY,
    data DATE NOT NULL DEFAULT CURRENT_DATE,
    mercado TEXT,
    total NUMERIC(10, 2),
    url_recibo TEXT,
    user_id UUID
);

-- Políticas de RLS (opcional)
-- ALTER TABLE itens_lista ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE historico_compras ENABLE ROW LEVEL SECURITY;

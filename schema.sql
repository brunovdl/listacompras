-- ─────────────────────────────────────────────────
-- Tabela de Listas de Compras
-- ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS listas (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    descricao TEXT,
    data DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────
-- Tabela para os Itens da Lista
-- ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS itens_lista (
    id SERIAL PRIMARY KEY,
    lista_id INTEGER REFERENCES listas(id) ON DELETE CASCADE,
    nome TEXT NOT NULL,
    categoria TEXT,
    comprado BOOLEAN DEFAULT FALSE,
    preco NUMERIC(10, 2),
    user_id UUID
);

-- ─────────────────────────────────────────────────
-- Tabela para o Histórico de Compras Finalizadas
-- ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS historico_compras (
    id SERIAL PRIMARY KEY,
    data DATE NOT NULL DEFAULT CURRENT_DATE,
    mercado TEXT,
    total NUMERIC(10, 2),
    url_recibo TEXT,
    user_id UUID
);

-- ─────────────────────────────────────────────────
-- Migração: adicionar lista_id se a coluna não existir
-- (executar no Supabase caso a tabela já exista)
-- ─────────────────────────────────────────────────
-- ALTER TABLE itens_lista
--     ADD COLUMN IF NOT EXISTS lista_id INTEGER REFERENCES listas(id) ON DELETE CASCADE;

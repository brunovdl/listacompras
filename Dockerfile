# ─── Build stage ────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Dependências do sistema para compilar pacotes nativos
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ─── Runtime stage ───────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# libzbar0: necessário para o pyzbar decodificar QR Codes
RUN apt-get update && apt-get install -y --no-install-recommends \
    libzbar0 \
    && rm -rf /var/lib/apt/lists/*

# Copiar dependências do build stage
COPY --from=builder /install /usr/local

# Copiar o código da aplicação
COPY . .

# Criar pasta de uploads
RUN mkdir -p uploads

# Expor a porta da aplicação
EXPOSE 8000

# Variáveis de ambiente padrão (sobrescreva no EasyPanel)
ENV HOST=0.0.0.0
ENV PORT=8000
ENV FLET_SECRET_KEY=mude_esta_chave_em_producao

# Comando de inicialização
CMD ["python", "main.py"]

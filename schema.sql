-- criando DB
CREATE DATABASE IF NOT EXISTS estoque
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE estoque;

-- Usuarios
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    usuario VARCHAR(50) NOT NULL UNIQUE,
    senha_hash VARCHAR(255) NOT NULL,
    perfil ENUM('admin', 'funcionario') NOT NULL DEFAULT 'funcionario',
    ativo TINYINT(1) NOT NULL DEFAULT 1,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- produtos
CREATE TABLE IF NOT EXISTS produtos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    codigo_barras VARCHAR(20) NULL UNIQUE,
    preco DECIMAL(10, 2) NOT NULL DEFAULT 0,
    quantidade INT NOT NULL DEFAULT 0,
    estoque_minimo INT NOT NULL DEFAULT 0,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_produtos_nome (nome)
);

-- movimentacoes
CREATE TABLE IF NOT EXISTS movimentacoes (
    id INT  AUTO_INCREMENT PRIMARY KEY,
    produto_id INT NOT NULL,
    usuario_id INT NOT NULL,
    tipo ENUM('entrada', 'saida') NOT NULL,
    quantidade INT NOT NULL,
    observacao VARCHAR(255) NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (produto_id) REFERENCES produtos (id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
    INDEX idx_movimentacoes_data (criado_em)
);


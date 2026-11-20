-- schema.sql  –  Conditional Transaction Engine
-- MySQL 8.0+  |  InnoDB  |  utf8mb4


CREATE DATABASE IF NOT EXISTS conditional_engine
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE conditional_engine;


-- accounts
CREATE TABLE IF NOT EXISTS accounts (
  account_id   INT           PRIMARY KEY AUTO_INCREMENT,
  account_name VARCHAR(100)  NOT NULL,
  balance      DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  created_at   TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_account_name            UNIQUE (account_name),
  CONSTRAINT chk_balance_non_negative   CHECK (balance >= 0),
  CONSTRAINT chk_account_name_not_empty CHECK (TRIM(account_name) != '')
) ENGINE=InnoDB;


-- contracts
CREATE TABLE IF NOT EXISTS contracts (
  contract_id         INT           PRIMARY KEY AUTO_INCREMENT,
  contract_name       VARCHAR(100)  NOT NULL,
  description         TEXT,
  min_sender_balance  DECIMAL(12,2) DEFAULT 0.00,
  max_transfer_amount DECIMAL(12,2) NOT NULL,
  is_active           BOOLEAN       DEFAULT TRUE,
  created_at          TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;


-- contract_conditions  (extensible; never execute stored expressions)
CREATE TABLE IF NOT EXISTS contract_conditions (
  condition_id    INT           PRIMARY KEY AUTO_INCREMENT,
  contract_id     INT           NOT NULL,
  condition_type  VARCHAR(50)   NOT NULL,
  condition_value DECIMAL(12,2),
  description     VARCHAR(255),
  FOREIGN KEY (contract_id) REFERENCES contracts(contract_id) ON DELETE CASCADE
) ENGINE=InnoDB;


-- transactions
CREATE TABLE IF NOT EXISTS transactions (
  transaction_id INT           PRIMARY KEY AUTO_INCREMENT,
  sender_id      INT           NOT NULL,
  receiver_id    INT           NOT NULL,
  contract_id    INT           NOT NULL,
  amount         DECIMAL(12,2) NOT NULL,
  status         ENUM('PENDING','SUCCESS','REJECTED') NOT NULL DEFAULT 'PENDING',
  message        VARCHAR(255),
  created_at     TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT chk_amount_positive        CHECK (amount > 0),
  CONSTRAINT chk_sender_receiver_differ CHECK (sender_id != receiver_id),
  FOREIGN KEY (sender_id)   REFERENCES accounts(account_id),
  FOREIGN KEY (receiver_id) REFERENCES accounts(account_id),
  FOREIGN KEY (contract_id) REFERENCES contracts(contract_id)
) ENGINE=InnoDB;


-- audit_logs
CREATE TABLE IF NOT EXISTS audit_logs (
  log_id         INT          PRIMARY KEY AUTO_INCREMENT,
  transaction_id INT,
  action         VARCHAR(100) NOT NULL,
  details        TEXT,
  created_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id) ON DELETE SET NULL
) ENGINE=InnoDB;


-- Indexes
-- Note: MySQL 8.0 does not support IF NOT EXISTS on standalone CREATE INDEX.
-- These are safe to re-run only on a fresh schema; use reset.sql to wipe & re-seed.
CREATE INDEX idx_transactions_sender   ON transactions(sender_id);
CREATE INDEX idx_transactions_receiver ON transactions(receiver_id);
CREATE INDEX idx_transactions_status   ON transactions(status);
CREATE INDEX idx_transactions_created  ON transactions(created_at);
CREATE INDEX idx_audit_transaction     ON audit_logs(transaction_id);

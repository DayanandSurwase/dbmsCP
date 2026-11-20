-- seed.sql  –  Demo data for Conditional Transaction Engine
-- Idempotent: uses INSERT IGNORE so it is safe to re-run

USE conditional_engine;

-- accounts
INSERT IGNORE INTO accounts (account_id, account_name, balance) VALUES
  (1, 'Alice', 5000.00),
  (2, 'Bob',   2000.00);


-- contracts
INSERT IGNORE INTO contracts
  (contract_id, contract_name, description, min_sender_balance, max_transfer_amount, is_active)
VALUES
  (1, 'Basic Transfer Contract',
      'Standard peer-to-peer transfer with minimum balance and amount cap',
      1000.00, 5000.00, TRUE);


-- contract_conditions
INSERT IGNORE INTO contract_conditions
  (condition_id, contract_id, condition_type, condition_value, description)
VALUES
  (1, 1, 'MIN_SENDER_BALANCE', 1000.00, 'Sender must retain at least ₹1000 after transfer'),
  (2, 1, 'MAX_TRANSFER_AMOUNT', 5000.00, 'Single transfer cannot exceed ₹5000');

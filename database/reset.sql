-- reset.sql  –  Wipe all data and re-seed
-- WARNING: destroys all transaction history

USE conditional_engine;

SET FOREIGN_KEY_CHECKS = 0;

TRUNCATE TABLE audit_logs;
TRUNCATE TABLE transactions;
TRUNCATE TABLE contract_conditions;
TRUNCATE TABLE contracts;
TRUNCATE TABLE accounts;

SET FOREIGN_KEY_CHECKS = 1;

-- Re-seed accounts
INSERT INTO accounts (account_id, account_name, balance) VALUES
  (1, 'Alice', 5000.00),
  (2, 'Bob',   2000.00);


-- Re-seed contracts
INSERT INTO contracts
  (contract_id, contract_name, description, min_sender_balance, max_transfer_amount, is_active)
VALUES
  (1, 'Basic Transfer Contract',
      'Standard peer-to-peer transfer with minimum balance and amount cap',
      1000.00, 5000.00, TRUE);


-- Re-seed contract_conditions
INSERT INTO contract_conditions
  (condition_id, contract_id, condition_type, condition_value, description)
VALUES
  (1, 1, 'MIN_SENDER_BALANCE',  1000.00, 'Sender must retain at least ₹1000 after transfer'),
  (2, 1, 'MAX_TRANSFER_AMOUNT', 5000.00, 'Single transfer cannot exceed ₹5000');

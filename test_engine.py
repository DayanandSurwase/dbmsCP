
from transaction_engine import execute_transfer

# Test 1: Valid transaction
result = execute_transfer(
    sender_id=1,
    receiver_id=2,
    contract_id=1,
    amount=1000
)

print("Test 1:", result)

# Test 2: Exceeds contract limit
result = execute_transfer(
    sender_id=1,
    receiver_id=2,
    contract_id=1,
    amount=10000
)

print("Test 2:", result)

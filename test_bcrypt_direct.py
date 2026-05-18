import bcrypt

plain_password = b"123456789"
hashed_password = b"$2b$12$FpAwciQU3G95S.HFaHFc2e34tSB5MVoO/3O55vcqiR/I7F887Pjhu"

try:
    result = bcrypt.checkpw(plain_password, hashed_password)
    print(f"Bcrypt verification result: {result}")
except Exception as e:
    print(f"ERROR: {e}")

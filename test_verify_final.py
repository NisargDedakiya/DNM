from backend.auth.security import verify_password

plain_password = "123456789"
hashed_password = "$2b$12$FpAwciQU3G95S.HFaHFc2e34tSB5MVoO/3O55vcqiR/I7F887Pjhu"

try:
    result = verify_password(plain_password, hashed_password)
    print(f"Password verification result: {result}")
except Exception as e:
    print(f"ERROR: {e}")

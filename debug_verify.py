from passlib.context import CryptContext
from backend.auth.security import verify_password

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
hashed_password = "$2b$12$FpAwciQU3G95S.HFaHFc2e34tSB5MVoO/3O55vcqiR/I7F887Pjhu"
plain_password = "123456789"

print(f"Hashed password string: {hashed_password}")
print(f"Length of hash: {len(hashed_password)}")
print(f"Identification: {pwd_context.identify(hashed_password)}")

try:
    result = verify_password(plain_password, hashed_password)
    print(f"Password verification result: {result}")
except Exception as e:
    print(f"ERROR: {e}")
    print(f"Error type: {type(e).__name__}")

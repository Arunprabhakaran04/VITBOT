from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated = "auto")

def encrypt(password: str)->str:
    return pwd_context.hash(password)

def verify(plain_pass : str, hash_pass : str):
    return pwd_context.verify(plain_pass, hash_pass)

    
import os
import secrets
import string

ALPHANUM = string.ascii_uppercase + string.digits

def generate_code() -> str:
    return "".join(secrets.choice(ALPHANUM) for _ in range(4)) + "-" + \
           "".join(secrets.choice(ALPHANUM) for _ in range(4))

def unique_filename(directory: str, ext: str, max_tries: int = 200) -> str:
    os.makedirs(directory, exist_ok=True)
    if not ext.startswith("."):
        ext = "." + ext

    for _ in range(max_tries):
        code = generate_code()
        path = os.path.join(directory, code + ext)
        if not os.path.exists(path):
            return path

    raise RuntimeError("Could not generate unique filename")

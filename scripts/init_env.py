"""Create local-only credentials without overwriting an existing .env."""

import secrets
from pathlib import Path

path = Path(__file__).resolve().parents[1] / ".env"
db_password = secrets.token_urlsafe(24)
content = (
    f"POSTGRES_PASSWORD={db_password}\n"
    f"DATABASE_URL=postgresql+psycopg://team:{db_password}@localhost:15432/team_directory\n"
    f"JWT_SECRET={secrets.token_urlsafe(48)}\n"
    f"DEMO_VIEWER_PASSWORD={secrets.token_urlsafe(16)}\n"
    f"DEMO_HR_PASSWORD={secrets.token_urlsafe(16)}\n"
    "ACCESS_TOKEN_MINUTES=30\nDB_POOL_SIZE=2\nPORT=8080\n"
)
with path.open("x") as file:
    path.chmod(0o600)
    file.write(content)
print("Created .env. Demo usernames are viewer and hr; their passwords are in .env.")

DOMAIN = "private_repo_loader"

# names used by the various modules ------------------------------
CONF_REPO  = "repository"
CONF_TOKEN = "token"          # preferred new name
CONF_PAT   = CONF_TOKEN       # <- <-- alias keeps old code working

# storage keys ----------------------------------------------------
STORAGE_VERSION = 1
STORAGE_KEY     = f"{DOMAIN}.storage"
DATA_REPOS      = "repos"

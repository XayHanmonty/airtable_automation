from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
# This makes them available via os.getenv()

env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

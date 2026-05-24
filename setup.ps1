# Setup script for Job Search Automator

Write-Host "Setting up Python virtual environment..."
python -m venv venv
.\venv\Scripts\Activate.ps1

Write-Host "Installing dependencies..."
pip install -r requirements.txt

Write-Host "Initializing database..."
python -c "from src.database import init_db; init_db()"

Write-Host "Setup complete! Please configure your .env file."

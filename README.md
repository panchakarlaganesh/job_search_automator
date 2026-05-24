# Job Search Automator

An automated, LLM-powered job search and application system for LinkedIn and Dice.

## Features
- **Multi-Source Scraping**: LinkedIn and Dice (via Apify).
- **LLM Evaluation**: Evaluates job descriptions against your resume (>60% match required).
- **Resume Tailoring**: Automatically modifies your resume (~30%) for each job.
- **Auto-Application**: Built-in support for Greenhouse and Lever (Playwright).
- **Learning Mode**: Remembers answers to application questions in a local database.
- **Streamlit Dashboard**: Track applications, view match scores, and handle manual interventions.
- **Notifications**: Telegram and Discord updates.
- **Scheduled Runs**: GitHub Actions workflow included.

## Setup
1. Clone the repository.
2. Run `powershell ./setup.ps1` to create the venv and install dependencies.
3. Configure your `.env` file (see `.env.example`).
4. Place your base resume(s) in the `resumes/` folder as `.md` files.
5. Update `config/search.json` with your target roles and locations.

## Usage
- **Run Automation**: `python main.py`
- **View Dashboard**: `streamlit run src/dashboard.py`
- **Learning Mode**: The bot will ask the LLM for answers to new questions and store them in `data/jobs.db`.

## GitHub Actions
Configure the following secrets in your GitHub repository:
- `APIFY_API_TOKEN`
- `OPENAI_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `DISCORD_WEBHOOK_URL`

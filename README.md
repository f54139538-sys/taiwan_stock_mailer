# Taiwan Stock Mailer

Streamlit app for looking up Taiwan stock prices, generating a short Gemini analysis report, and emailing the report through Gmail.

## Local Setup

Create a `.env` file:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GMAIL_USER=your_gmail_address@gmail.com
GMAIL_APP_PASSWORD=your_16_character_app_password
```

Install dependencies:

```powershell
py -m pip install -r requirements.txt
```

Run the app:

```powershell
py -m streamlit run app.py
```

## Streamlit Cloud Secrets

Add these values in Streamlit Cloud app settings:

```toml
GEMINI_API_KEY = "your_gemini_api_key_here"
GMAIL_USER = "your_gmail_address@gmail.com"
GMAIL_APP_PASSWORD = "your_16_character_app_password"
```

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/analytics.readonly",
]

flow = InstalledAppFlow.from_client_secrets_file(
    "client_secret.json",
    scopes=SCOPES,
)

credentials = flow.run_local_server(
    host="localhost",
    port=0,
    open_browser=True,
    access_type="offline",
    prompt="consent",
    authorization_prompt_message="Opening Google authorization...",
    success_message="Authorization successful. You can close this window.",
)

print("\nNEW GSC_REFRESH_TOKEN:")
print(credentials.refresh_token)
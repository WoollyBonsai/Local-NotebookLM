class Settings:
    def __init__(self):
        self.LOCAL_LLM_ENDPOINT = "http://localhost:11434"
        self.CLOUD_LLM_ENDPOINT = ""
        self.LOCAL_MODEL = "ollama/llama3.1"
        self.CLOUD_MODEL = "ollama/llama3.1"

settings = Settings()

import warnings
# This blocks the deprecation error thrown by Chromadb usage...
warnings.filterwarnings("ignore", category=FutureWarning)

from agent.gemini_agent import GeminiAgent

def main():
    agent = GeminiAgent()
    try:
        agent.run()
    except KeyboardInterrupt as e:
        print(f"Process interrupted: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()

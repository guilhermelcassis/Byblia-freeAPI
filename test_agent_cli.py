import asyncio
import argparse
from app.services.ai_agent import generate_streaming_response

async def chat_with_agent(question: str):
    """Stream the agent's response to a question"""
    print("\nAgent is thinking...\n")
    async for response in generate_streaming_response(question):
        if isinstance(response, str):
            # Print streaming text chunks
            print(response, end="", flush=True)
        else:
            # Print metadata when received
            print("\n\n---\nMetadata:")
            print(f"Tokens used: {response['token_usage']}")
            print(f"Temperature: {response['temperature']}")
            if response['interaction_id']:
                print(f"Interaction ID: {response['interaction_id']}")

def main():
    parser = argparse.ArgumentParser(description="Chat with AI Agent")
    parser.add_argument(
        "question", 
        nargs="?",  # Make the question optional
        help="The question to ask the AI agent"
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Run in interactive mode (keep chatting until 'exit')"
    )
    
    args = parser.parse_args()
    
    if args.interactive:
        print("Interactive mode - type 'exit' to quit")
        while True:
            question = input("\nYou: ")
            if question.lower() in ['exit', 'quit']:
                break
            asyncio.run(chat_with_agent(question))
    elif args.question:
        asyncio.run(chat_with_agent(args.question))
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 
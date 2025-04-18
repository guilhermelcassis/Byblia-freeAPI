import asyncio
import argparse
from app.services.ai_agent import generate_streaming_response

async def chat_with_agent(question: str, message_history=None):
    """
    Stream the agent's response to a question
    
    Args:
        question: The question to ask
        message_history: Optional history of previous messages
        
    Returns:
        The updated message history
    """
    print("\nAgent is thinking...\n")
    new_messages = None
    
    async for response in generate_streaming_response(question, message_history=message_history):
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
            
            # Save new messages for context
            new_messages = response.get('new_messages')
            if new_messages:
                print(f"Message history updated ({len(new_messages)} messages)")
    
    return new_messages

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
    parser.add_argument(
        "-c", "--context",
        action="store_true",
        help="Keep conversation context between messages"
    )
    
    args = parser.parse_args()
    
    if args.interactive:
        message_history = None
        print("Interactive mode - type 'exit' to quit")
        print(f"Conversation context: {'ON' if args.context else 'OFF'}")
        
        while True:
            question = input("\nYou: ")
            if question.lower() in ['exit', 'quit']:
                break
            
            if args.context:
                # Use conversation history for context
                message_history = asyncio.run(chat_with_agent(question, message_history))
            else:
                # No conversation context
                asyncio.run(chat_with_agent(question))
    elif args.question:
        asyncio.run(chat_with_agent(args.question))
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 
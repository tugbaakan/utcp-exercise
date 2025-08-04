"""
UTCP Europcar API with LLM Integration Example

This example demonstrates how to:
1. Initialize a UTCP client with the Europcar API provider
2. Use OpenAI GPT models to understand user requests in natural language
3. Automatically search for relevant Europcar API tools based on user intent
4. Execute tool calls through the LLM and provide natural language responses
5. Maintain conversation context for follow-up questions

Features:
- Natural language interaction with Europcar API
- Automatic tool discovery and selection
- Intelligent parameter extraction and validation
- Conversational follow-up and error handling
- Support for complex multi-step car rental workflows

Make sure to configure your API credentials in the .env file before running.
"""

import asyncio
import os
import json
import sys
import re
from pathlib import Path
from typing import Dict, Any, List

import openai
from dotenv import load_dotenv

from utcp.client.utcp_client import UtcpClient
from utcp.client.utcp_client_config import UtcpClientConfig, UtcpDotEnv
from utcp.shared.tool import Tool


class EuropcarLLMAssistant:
    """An LLM-powered assistant for interacting with the Europcar API."""
    
    def __init__(self, utcp_client: UtcpClient, openai_client: openai.AsyncOpenAI):
        self.utcp_client = utcp_client
        self.openai_client = openai_client
        self.conversation_history = []
        self.available_tools = []
    
    async def initialize(self) -> bool:
        """Initialize the assistant and load available tools."""
        try:
            self.available_tools = await self.utcp_client.tool_repository.get_tools()
            if not self.available_tools:
                print("❌ Error: No Europcar API tools found.")
                print("   This usually means the API spec couldn't be loaded.")
                print("   Check your providers.json and .env configuration.")
                return False
            
            print(f"✅ Successfully loaded {len(self.available_tools)} Europcar API tools")
            print("🚗 Europcar LLM Assistant ready! You can now ask me about:")
            print("   • Finding car rental locations")
            print("   • Searching for available vehicles")
            print("   • Making reservations")
            print("   • Checking pricing and availability")
            print("   • Managing bookings")
            print("\nJust ask me in natural language what you'd like to do!")
            return True
            
        except Exception as e:
            print(f"❌ Error initializing assistant: {str(e)}")
            return False
    
    def format_tools_for_llm(self, tools: List[Tool]) -> str:
        """Format tools for inclusion in the LLM prompt."""
        if not tools:
            return json.dumps([], indent=2)
            
        tool_descriptions = []
        for tool in tools:
            if not tool or not hasattr(tool, 'name'):
                continue  # Skip invalid tools
                
            tool_info = {
                "name": getattr(tool, 'name', 'Unknown Tool'),
                "description": getattr(tool, 'description', None) or "No description available",
            }
            
            # Add parameter information
            if hasattr(tool, 'inputs') and tool.inputs:
                if hasattr(tool.inputs, 'properties') and tool.inputs.properties:
                    properties = tool.inputs.properties
                    required = getattr(tool.inputs, 'required', []) or []
                    
                    params = {}
                    for param_name, param_info in properties.items():
                        if param_info:  # Check if param_info is not None
                            params[param_name] = {
                                "type": param_info.get('type', 'string') if isinstance(param_info, dict) else 'string',
                                "description": param_info.get('description', 'No description') if isinstance(param_info, dict) else 'No description',
                                "required": param_name in required
                            }
                    if params:  # Only add parameters if we have any
                        tool_info["parameters"] = params
            
            tool_descriptions.append(tool_info)
        
        return json.dumps(tool_descriptions, indent=2)
    
    async def search_relevant_tools(self, user_request: str, limit: int = 10) -> List[Tool]:
        """Search for tools relevant to the user's request."""
        try:
            relevant_tools = await self.utcp_client.search_tools(user_request, limit=limit)
            return relevant_tools if relevant_tools is not None else []
        except Exception as e:
            print(f"⚠️  Warning: Error searching tools: {str(e)}")
            # Fallback to first few tools, ensuring we have a valid list
            fallback_tools = self.available_tools[:limit] if self.available_tools else []
            return fallback_tools
    
    async def get_llm_response(self, user_request: str, relevant_tools: List[Tool]) -> str:
        """Get an LLM response for the user request with available tools."""
        tools_json = self.format_tools_for_llm(relevant_tools)
        
        system_prompt = f"""You are a helpful assistant for the Europcar car rental service. You can help users with car rentals, finding locations, checking availability, making reservations, and more.

When you need to use a tool to help the user, respond with a JSON object containing:
- "tool_name": the exact name of the tool to use
- "arguments": an object with the required parameters

For example: {{"tool_name": "SearchStations", "arguments": {{"searchTerm": "istanbul"}}}}

Available Europcar API tools:
{tools_json}

Guidelines:
1. Always be helpful and friendly
2. If you need to use a tool, ONLY respond with the JSON object, no additional text
3. If you can answer without a tool, provide a natural conversational response
4. Ask for clarification if the user's request is unclear
5. Focus on car rental related tasks (finding cars, locations, pricing, bookings)
6. If the user asks about something unrelated to car rentals, politely redirect them
"""
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        if self.conversation_history:
            messages.extend(self.conversation_history)
        
        # Add current user request
        messages.append({"role": "user", "content": user_request})
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"I apologize, but I'm having trouble processing your request right now. Error: {str(e)}"
    
    async def execute_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool call and return the result."""
        try:
            print(f"🔧 Executing: {tool_name}")
            print(f"📝 Parameters: {json.dumps(arguments, indent=2)}")
            
            result = await self.utcp_client.call_tool(tool_name, arguments)
            return json.dumps(result, indent=2) if result else "No data returned"
            
        except Exception as e:
            error_msg = f"Error executing {tool_name}: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg
    
    async def handle_user_request(self, user_request: str) -> str:
        """Handle a user request and return the response."""
        print(f"\n🔍 Processing: {user_request}")
        
        try:
            # Search for relevant tools
            relevant_tools = await self.search_relevant_tools(user_request)
            print(f"🛠️  Found {len(relevant_tools)} relevant tools")
            
            # Get LLM response
            llm_response = await self.get_llm_response(user_request, relevant_tools)
            print(f"🤖 LLM Response: {llm_response}")
        except Exception as e:
            print(f"❌ Error during request processing: {str(e)}")
            return f"I apologize, but I encountered an error while processing your request: {str(e)}. Please try rephrasing your question or ask for help."
        
        # Check if the response contains a tool call
        # First, check if the response looks like JSON and contains tool_name and arguments
        tool_call_json = None
        
        if '"tool_name"' in llm_response and '"arguments"' in llm_response:
            # Try to extract JSON from the response
            llm_response_stripped = llm_response.strip()
            
            # If the response starts and ends with braces, try parsing it directly
            if llm_response_stripped.startswith('{') and llm_response_stripped.endswith('}'):
                tool_call_json = llm_response_stripped
            else:
                # Otherwise, try to find JSON within the response
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', llm_response, re.DOTALL)
                if json_match:
                    tool_call_json = json_match.group(0)
                else:
                    # Fallback: try to find the JSON by matching balanced braces
                    start = llm_response.find('{')
                    if start != -1:
                        brace_count = 0
                        end = start
                        for i, char in enumerate(llm_response[start:], start):
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    end = i + 1
                                    break
                        if end > start:
                            tool_call_json = llm_response[start:end]
        
        print(f"🔍 Extracted JSON: {tool_call_json}")
 
        if tool_call_json:
            try:
                # Parse the tool call
                tool_call_data = json.loads(tool_call_json)
                
                if "tool_name" in tool_call_data and "arguments" in tool_call_data:
                    tool_name = tool_call_data["tool_name"]
                    arguments = tool_call_data["arguments"]
                    
                    # Execute the tool
                    tool_result = await self.execute_tool_call(tool_name, arguments)
                    
                    # Get LLM interpretation of the results
                    interpretation_prompt = f"""The user asked: "{user_request}"

I executed the tool "{tool_name}" with arguments {json.dumps(arguments)} and got this result:

{tool_result}

Please provide a helpful, natural language response to the user based on this result. Format the information in a user-friendly way and highlight the most relevant details."""
                    
                    interpretation_response = await self.openai_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are a helpful Europcar assistant. Interpret tool results and provide friendly, informative responses to users."},
                            {"role": "user", "content": interpretation_prompt}
                        ],
                        temperature=0.7,
                        max_tokens=1000
                    )
                    
                    final_response = interpretation_response.choices[0].message.content
                    
                    # Update conversation history
                    self.conversation_history.append({"role": "user", "content": user_request})
                    self.conversation_history.append({"role": "assistant", "content": final_response})
                    
                    # Keep conversation history manageable
                    if len(self.conversation_history) > 20:
                        self.conversation_history = self.conversation_history[-20:]
                    
                    return final_response
                
            except json.JSONDecodeError as e:
                print(f"⚠️  Could not parse tool call JSON: {e}")
                return llm_response
            except Exception as e:
                print(f"⚠️  Error processing tool call: {e}")
                return llm_response
        
        # No tool call needed, return the LLM response directly
        self.conversation_history.append({"role": "user", "content": user_request})
        self.conversation_history.append({"role": "assistant", "content": llm_response})
        
        # Keep conversation history manageable
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
        
        return llm_response


async def initialize_utcp_client() -> UtcpClient:
    """Initialize the UTCP client with Europcar API configuration."""
    config = UtcpClientConfig(
        providers_file_path=str(Path(__file__).parent / "providers.json"),
        load_variables_from=[
            UtcpDotEnv(env_file_path=str(Path(__file__).parent / ".env"))
        ]
    )
    
    client = await UtcpClient.create(config)
    return client


async def main():
    """Main function to run the Europcar LLM assistant."""
    # Load environment variables
    load_dotenv(Path(__file__).parent / ".env")
    
    print("🚗 Europcar LLM Assistant")
    print("=" * 40)
    print("Initializing...")
    
    # Check for required API keys
    if not os.environ.get("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found in environment variables")
        print("   Please add your OpenAI API key to the .env file:")
        print("   OPENAI_API_KEY=your_openai_api_key_here")
        sys.exit(1)
    
    if not os.environ.get("EUROPCAR_API_API_KEY"):
        print("⚠️  Warning: EUROPCAR_API_API_KEY not found in environment variables")
        print("   Some Europcar API features may not work without authentication")
    
    try:
        # Initialize clients
        print("🔧 Initializing UTCP client...")
        utcp_client = await initialize_utcp_client()
        
        print("🤖 Initializing OpenAI client...")
        openai_client = openai.AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        # Create assistant
        assistant = EuropcarLLMAssistant(utcp_client, openai_client)
        
        # Initialize assistant and check if ready
        if not await assistant.initialize():
            print("\n❌ Failed to initialize the assistant. Please check your configuration.")
            return
        
        # Main conversation loop
        print("\n" + "=" * 60)
        print("💬 Chat with the Europcar Assistant (type 'exit' to quit)")
        print("=" * 60)
        
        while True:
            try:
                user_input = input("\n🧑 You: ").strip()
                
                if not user_input:
                    print("🤖 I'm here to help! Please tell me what you'd like to do.")
                    continue
                
                if user_input.lower() in ['exit', 'quit', 'bye', 'goodbye']:
                    print("\n🤖 Thank you for using the Europcar LLM Assistant!")
                    print("   Have a great day! 🚗✨")
                    break
                
                # Process the user request
                response = await assistant.handle_user_request(user_input)
                print(f"\n🤖 Assistant: {response}")
                
            except KeyboardInterrupt:
                print("\n\n🤖 Chat interrupted. Thanks for using the Europcar Assistant!")
                break
            except Exception as e:
                print(f"\n❌ An error occurred: {str(e)}")
                print("🤖 Please try again or rephrase your request.")
    
    except Exception as e:
        print(f"\n❌ Failed to initialize: {str(e)}")
        print("🤖 Please check your configuration and try again.")


if __name__ == "__main__":
    asyncio.run(main())
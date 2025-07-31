"""
Robust UTCP OpenAI Integration Example

This version handles missing API keys gracefully and won't hang.
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


async def initialize_utcp_client() -> UtcpClient:
    """Initialize the UTCP client with configuration."""
    config = UtcpClientConfig(
        providers_file_path=str(Path(__file__).parent / "providers.json"),
        load_variables_from=[
            UtcpDotEnv(env_file_path=str(Path(__file__).parent / ".env"))
        ]
    )
    
    client = await UtcpClient.create(config)
    return client


def check_api_keys():
    """Check which API keys are available."""
    keys_status = {
        'openai': bool(os.environ.get("OPENAI_API_KEY")),
        'newsapi': bool(os.environ.get("NEWS_API_KEY")),
    }
    return keys_status


def filter_tools_by_available_keys(tools: List[Tool], keys_status: Dict[str, bool]) -> List[Tool]:
    """Filter tools based on available API keys."""
    available_tools = []
    
    # Safe keywords for OpenAI tools
    safe_keywords = ['list', 'get', 'retrieve', 'search']
    unsafe_keywords = ['create', 'delete', 'cancel', 'modify', 'update', 'fine', 'training', 'upload']
    
    for tool in tools:
        tool_name_lower = tool.name.lower()
        
        # OpenLibrary tools - always work
        if tool.name.startswith('openlibrary.'):
            available_tools.append(tool)
            continue
            
        # NewsAPI tools - only if key is available
        if tool.name.startswith('newsapi.'):
            if keys_status.get('newsapi', False):
                available_tools.append(tool)
            # Skip NewsAPI tools if no key
            continue
            
        # OpenAI tools - only if key is available and tool is safe
        if tool.name.startswith('openai.'):
            if keys_status.get('openai', False):
                has_safe = any(keyword in tool_name_lower for keyword in safe_keywords)
                has_unsafe = any(keyword in tool_name_lower for keyword in unsafe_keywords)
                
                if has_safe and not has_unsafe:
                    if not any(complex_word in tool_name_lower for complex_word in ['batch', 'eval', 'thread', 'run']):
                        available_tools.append(tool)
    
    return available_tools


def format_tools_for_prompt(tools: List[Tool]) -> str:
    """Convert UTCP tools to a JSON string for the prompt."""
    tool_list = []
    for tool in tools:
        tool_dict = {
            "name": tool.name,
            "description": tool.description,
            "inputs": tool.inputs.model_dump() if tool.inputs else {}
        }
        tool_list.append(tool_dict)
    return json.dumps(tool_list, indent=2)


async def get_openai_response(messages: List[Dict[str, str]]) -> str:
    """Get a response from OpenAI."""
    client = openai.AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.1,
    )
    
    return response.choices[0].message.content


async def safe_call_tool(utcp_client: UtcpClient, tool_name: str, arguments: Dict[str, Any], timeout: int = 30) -> tuple[bool, Any]:
    """Safely call a tool with timeout and error handling."""
    try:
        # Use asyncio.wait_for to add timeout
        result = await asyncio.wait_for(
            utcp_client.call_tool(tool_name, arguments),
            timeout=timeout
        )
        return True, result
    except asyncio.TimeoutError:
        error_msg = f"Tool {tool_name} timed out after {timeout} seconds"
        print(f"⏰ {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = f"Error calling {tool_name}: {str(e)}"
        print(f"🚨 {error_msg}")
        return False, error_msg


async def main():
    """Main function with robust error handling."""
    load_dotenv(Path(__file__).parent / ".env")
    
    print("🛡️ Robust UTCP + OpenAI Integration")
    print("=" * 50)
    
    # Check available API keys
    keys_status = check_api_keys()
    print("🔑 API Key Status:")
    for service, available in keys_status.items():
        status = "✅ Available" if available else "❌ Missing"
        print(f"   • {service.upper()}: {status}")
    
    if not keys_status['openai']:
        print("\n❌ Error: OPENAI_API_KEY is required for this example")
        print("Please add it to your .env file")
        sys.exit(1)
    
    if not keys_status['newsapi']:
        print("\n⚠️  NewsAPI tools will be disabled (no NEWS_API_KEY)")
        print("   Get a free key at: https://newsapi.org/")
    
    print("\nInitializing UTCP client...")
    utcp_client = await initialize_utcp_client()
    print("✅ UTCP client initialized successfully.")

    # Get tools and filter by available keys
    all_tools = await utcp_client.tool_repository.get_tools()
    available_tools = filter_tools_by_available_keys(all_tools, keys_status)
    
    print(f"\n📊 Tool Summary:")
    print(f"   • Total tools: {len(all_tools)}")
    print(f"   • Available tools: {len(available_tools)}")
    
    # Show breakdown by provider
    by_provider = {}
    for tool in available_tools:
        provider = tool.name.split('.')[0]
        by_provider[provider] = by_provider.get(provider, 0) + 1
    
    for provider, count in by_provider.items():
        print(f"   • {provider}: {count} available tools")

    conversation_history = []

    print(f"\n💬 Chat Mode (using {len(available_tools)} available tools)")
    print("=" * 50)
    print("💡 Tip: Try 'list OpenAI models' or 'search for Python books'")

    while True:
        user_prompt = input("\nEnter your prompt (or 'exit' to quit): ")
        if user_prompt.lower() in ["exit", "quit"]:
            break

        print(f"\n🔍 Searching for relevant tools...")
        relevant_tools = await utcp_client.search_tools(user_prompt, limit=10)
        
        # Filter to only available tools
        available_relevant_tools = [tool for tool in relevant_tools if tool in available_tools]
        
        if available_relevant_tools:
            print(f"✅ Found {len(available_relevant_tools)} available, relevant tools:")
            for i, tool in enumerate(available_relevant_tools[:5], 1):
                print(f"   {i}. {tool.name}")
        else:
            print("⚠️  No available relevant tools found.")
            # Check if NewsAPI tools were found but not available
            newsapi_relevant = [tool for tool in relevant_tools if tool.name.startswith('newsapi.')]
            if newsapi_relevant and not keys_status['newsapi']:
                print("💡 News tools found but NEWS_API_KEY is missing!")
                print("   Get free key at: https://newsapi.org/")
            
            print("🔄 Using general available tools...")
            available_relevant_tools = available_tools[:5]

        tools_json_string = format_tools_for_prompt(available_relevant_tools)

        system_prompt = (
            "You are a helpful assistant that actively uses available tools to provide current information. "
            "When a user asks for current/real-time information and you have relevant tools, "
            "IMMEDIATELY call the appropriate tool by responding with ONLY a JSON object: "
            "{\"tool_name\": \"tool.name\", \"arguments\": {\"param\": \"value\"}}. "
            "Do NOT ask for permission - just call the tool directly. "
            "ONLY use tools from the provided list. Do not invent tool names. "
            f"Available tools:\n{tools_json_string}"
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(conversation_history[-6:])
        messages.append({"role": "user", "content": user_prompt})

        print(f"\n🤖 Getting response from OpenAI...")
        try:
            assistant_response = await get_openai_response(messages)
        except Exception as e:
            print(f"❌ OpenAI API error: {e}")
            continue

        # Try to parse tool call - be more flexible with JSON detection
        json_match = re.search(r'```json\n({.*?})\n```', assistant_response, re.DOTALL)
        if not json_match:
            # Look for complete JSON object with tool_name - use balanced braces
            json_match = re.search(r'(\{(?:[^{}]|{[^{}]*})*"tool_name"(?:[^{}]|{[^{}]*})*\})', assistant_response, re.DOTALL)
        if not json_match:
            # Fallback: any JSON-like object with balanced braces
            json_match = re.search(r'(\{(?:[^{}]|{[^{}]*})*\})', assistant_response, re.DOTALL)

        if json_match:
            json_string = json_match.group(1)
            print(f"🔍 Found JSON: {json_string}")
            try:
                tool_call_data = json.loads(json_string)
                if "tool_name" in tool_call_data and "arguments" in tool_call_data:
                    tool_name = tool_call_data["tool_name"]
                    arguments = tool_call_data["arguments"]
                    
                    print(f"\n🔧 Executing tool call: {tool_name}")
                    print(f"📋 Arguments: {json.dumps(arguments, indent=2)}")

                    # Call tool with timeout
                    success, result = await safe_call_tool(utcp_client, tool_name, arguments, timeout=30)
                    
                    if success:
                        print(f"✅ Tool call successful!")
                        print(f"📄 Result preview: {str(result)[:300]}...")
                        
                        # Get final response from OpenAI
                        conversation_history.extend([
                            {"role": "user", "content": user_prompt},
                            {"role": "assistant", "content": assistant_response}
                        ])
                        
                        follow_up_messages = [
                            {"role": "system", "content": "Provide a helpful summary of the tool results."},
                            *conversation_history[-4:],
                            {"role": "user", "content": f"Tool '{tool_name}' returned: {str(result)[:800]}... Please summarize this helpfully."}
                        ]
                        
                        try:
                            final_response = await get_openai_response(follow_up_messages)
                            print(f"\n🎯 Assistant: {final_response}")
                            conversation_history.append({"role": "assistant", "content": final_response})
                        except Exception as e:
                            print(f"❌ Error getting summary: {e}")
                    else:
                        print(f"❌ Tool call failed: {result}")
                        print("💡 Tip: Some tools may need API keys or specific parameters")
                        conversation_history.extend([
                            {"role": "user", "content": user_prompt},
                            {"role": "assistant", "content": f"I tried to use {tool_name} but encountered an error. {result}"}
                        ])
                else:
                    print(f"\n💬 Assistant: {assistant_response}")
                    conversation_history.extend([
                        {"role": "user", "content": user_prompt},
                        {"role": "assistant", "content": assistant_response}
                    ])
            except json.JSONDecodeError:
                print(f"\n💬 Assistant: {assistant_response}")
                conversation_history.extend([
                    {"role": "user", "content": user_prompt},
                    {"role": "assistant", "content": assistant_response}
                ])
        else:
            print(f"\n💬 Assistant: {assistant_response}")
            conversation_history.extend([
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": assistant_response}
            ])

    print(f"\n👋 Thanks for using Robust UTCP + OpenAI!")


if __name__ == "__main__":
    asyncio.run(main()) 
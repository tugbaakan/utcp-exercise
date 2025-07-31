"""
Improved UTCP OpenAI Integration Example

This example demonstrates how to:
1. Initialize a UTCP client with tool providers
2. Use SAFE OpenAI tools that actually work
3. Handle errors gracefully
4. Provide better tool filtering for LLM integration
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


def filter_safe_tools(tools: List[Tool]) -> List[Tool]:
    """Filter tools to only include safe ones that don't require complex parameters."""
    safe_tools = []
    
    # Safe keywords - tools that typically work without complex setup
    safe_keywords = ['list', 'get', 'retrieve', 'search']
    
    # Unsafe keywords - tools that need specific parameters or modify state
    unsafe_keywords = ['create', 'delete', 'cancel', 'modify', 'update', 'fine', 'training', 'upload']
    
    for tool in tools:
        tool_name_lower = tool.name.lower()
        
        # Include OpenLibrary tools (they work well)
        if tool.name.startswith('openlibrary.'):
            safe_tools.append(tool)
            continue
            
        # Include NewsAPI tools (if API key is configured)
        if tool.name.startswith('newsapi.'):
            safe_tools.append(tool)
            continue
            
        # For OpenAI tools, be more selective
        if tool.name.startswith('openai.'):
            # Include if it has safe keywords and no unsafe keywords
            has_safe = any(keyword in tool_name_lower for keyword in safe_keywords)
            has_unsafe = any(keyword in tool_name_lower for keyword in unsafe_keywords)
            
            if has_safe and not has_unsafe:
                # Additional check: avoid tools that need complex parameters
                if not any(complex_word in tool_name_lower for complex_word in ['batch', 'eval', 'thread', 'run']):
                    safe_tools.append(tool)
    
    return safe_tools


def format_tools_for_prompt(tools: List[Tool]) -> str:
    """Convert UTCP tools to a JSON string for the prompt."""
    tool_list = []
    for tool in tools:
        # Simplify tool representation for LLM
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
        temperature=0.1,  # Lower temperature for more consistent tool calling
    )
    
    return response.choices[0].message.content


async def safe_call_tool(utcp_client: UtcpClient, tool_name: str, arguments: Dict[str, Any]) -> tuple[bool, Any]:
    """Safely call a tool with error handling."""
    try:
        result = await utcp_client.call_tool(tool_name, arguments)
        return True, result
    except Exception as e:
        error_msg = f"Error calling {tool_name}: {str(e)}"
        print(f"🚨 {error_msg}")
        return False, error_msg


async def main():
    """Main function to demonstrate improved OpenAI with UTCP integration."""
    load_dotenv(Path(__file__).parent / ".env")
    
    if not os.environ.get("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found in environment variables")
        print("Please set it in the .env file")
        sys.exit(1)
    
    print("🚀 Improved UTCP + OpenAI Integration")
    print("=" * 50)
    print("Initializing UTCP client...")
    utcp_client = await initialize_utcp_client()
    print("✅ UTCP client initialized successfully.")

    # Get all tools and filter to safe ones
    all_tools = await utcp_client.tool_repository.get_tools()
    safe_tools = filter_safe_tools(all_tools)
    
    print(f"\n📊 Tool Summary:")
    print(f"   • Total tools: {len(all_tools)}")
    print(f"   • Safe tools: {len(safe_tools)}")
    
    # Show breakdown by provider
    safe_by_provider = {}
    for tool in safe_tools:
        provider = tool.name.split('.')[0]
        safe_by_provider[provider] = safe_by_provider.get(provider, 0) + 1
    
    for provider, count in safe_by_provider.items():
        print(f"   • {provider}: {count} safe tools")

    conversation_history = []

    print(f"\n💬 Chat Mode (using {len(safe_tools)} safe tools)")
    print("=" * 50)

    while True:
        user_prompt = input("\nEnter your prompt (or 'exit' to quit): ")
        if user_prompt.lower() in ["exit", "quit"]:
            break

        print(f"\n🔍 Searching for relevant tools...")
        relevant_tools = await utcp_client.search_tools(user_prompt, limit=10)
        
        # Filter relevant tools to only safe ones
        safe_relevant_tools = [tool for tool in relevant_tools if tool in safe_tools]
        
        if safe_relevant_tools:
            print(f"✅ Found {len(safe_relevant_tools)} safe, relevant tools:")
            for i, tool in enumerate(safe_relevant_tools[:5], 1):
                print(f"   {i}. {tool.name}")
        else:
            print("⚠️  No safe relevant tools found for this query.")
            # Continue anyway with a general response
            safe_relevant_tools = safe_tools[:5]  # Use first 5 safe tools
            print(f"🔄 Using general safe tools instead...")

        tools_json_string = format_tools_for_prompt(safe_relevant_tools)

        system_prompt = (
            "You are a helpful assistant. When you can help with a task using the available tools, "
            "respond with a JSON object with 'tool_name' and 'arguments' keys. "
            "ONLY use tools from the list provided. Do not invent tool names. "
            "For list/get tools, you usually don't need many parameters. "
            "If you cannot help with the available tools, just respond normally. "
            f"Available tools:\n{tools_json_string}"
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(conversation_history[-6:])  # Keep last 6 messages for context
        messages.append({"role": "user", "content": user_prompt})

        print(f"\n🤖 Getting response from OpenAI...")
        assistant_response = await get_openai_response(messages)

        # Try to parse tool call
        json_match = re.search(r'```json\n({.*?})\n```', assistant_response, re.DOTALL)
        if not json_match:
            json_match = re.search(r'({.*?})', assistant_response, re.DOTALL)

        if json_match:
            json_string = json_match.group(1)
            try:
                tool_call_data = json.loads(json_string)
                if "tool_name" in tool_call_data and "arguments" in tool_call_data:
                    tool_name = tool_call_data["tool_name"]
                    arguments = tool_call_data["arguments"]
                    
                    print(f"\n🔧 Executing tool call: {tool_name}")
                    print(f"📋 Arguments: {json.dumps(arguments, indent=2)}")

                    success, result = await safe_call_tool(utcp_client, tool_name, arguments)
                    
                    if success:
                        print(f"✅ Tool call successful!")
                        print(f"📄 Result preview: {str(result)[:200]}...")
                        
                        # Get final response from OpenAI
                        conversation_history.extend([
                            {"role": "user", "content": user_prompt},
                            {"role": "assistant", "content": assistant_response}
                        ])
                        
                        follow_up_messages = [
                            {"role": "system", "content": "Provide a helpful summary of the tool results to the user."},
                            *conversation_history[-4:],
                            {"role": "user", "content": f"Tool '{tool_name}' returned: {str(result)[:500]}... Please summarize this helpfully."}
                        ]
                        
                        final_response = await get_openai_response(follow_up_messages)
                        print(f"\n🎯 Assistant: {final_response}")
                        conversation_history.append({"role": "assistant", "content": final_response})
                    else:
                        print(f"❌ Tool call failed: {result}")
                        conversation_history.extend([
                            {"role": "user", "content": user_prompt},
                            {"role": "assistant", "content": f"I tried to use {tool_name} but got an error: {result}. Let me try to help differently."}
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

    print(f"\n👋 Thanks for using UTCP + OpenAI!")


if __name__ == "__main__":
    asyncio.run(main()) 
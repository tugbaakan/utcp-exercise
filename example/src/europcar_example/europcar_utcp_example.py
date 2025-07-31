"""
UTCP Europcar API Integration Example

This example demonstrates how to:
1. Initialize a UTCP client with the Europcar API provider
2. Search for relevant tools from the Europcar API
3. Execute tool calls to interact with Europcar services
4. Handle API responses and errors gracefully

Make sure to configure your API credentials in the .env file before running.
"""

import asyncio
import os
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

from dotenv import load_dotenv

from utcp.client.utcp_client import UtcpClient
from utcp.client.utcp_client_config import UtcpClientConfig, UtcpDotEnv
from utcp.shared.tool import Tool


async def initialize_utcp_client() -> UtcpClient:
    """Initialize the UTCP client with Europcar API configuration."""
    # Create a configuration for the UTCP client
    config = UtcpClientConfig(
        providers_file_path=str(Path(__file__).parent / "providers.json"),
        load_variables_from=[
            UtcpDotEnv(env_file_path=str(Path(__file__).parent / ".env"))
        ]
    )
    
    # Create and return the UTCP client
    client = await UtcpClient.create(config)
    return client


def display_tools(tools: List[Tool]) -> None:
    """Display available tools in a formatted way."""
    if not tools:
        print("No tools found.")
        return
    
    print("\nAvailable Europcar API tools:")
    print("-" * 50)
    for i, tool in enumerate(tools, 1):
        print(f"{i}. {tool.name}")
        if tool.description:
            print(f"   Description: {tool.description}")
        print(f"   Method: {getattr(tool, 'method', 'N/A')}")
        if hasattr(tool, 'parameters') and tool.parameters:
            print(f"   Parameters: {list(tool.parameters.get('properties', {}).keys())}")
        print()


async def interactive_tool_call(client: UtcpClient, tools: List[Tool]) -> None:
    """Allow user to interactively select and call tools."""
    if not tools:
        print("No tools available for calling.")
        return
    
    print("\nSelect a tool to call (enter number):")
    try:
        choice = int(input("Tool number: ")) - 1
        if 0 <= choice < len(tools):
            selected_tool = tools[choice]
            print(f"\nSelected tool: {selected_tool.name}")
            
            # Get parameters if the tool requires them
            arguments = {}
            if hasattr(selected_tool, 'parameters') and selected_tool.parameters:
                properties = selected_tool.parameters.get('properties', {})
                if properties:
                    print("\nTool parameters:")
                    for param_name, param_info in properties.items():
                        param_type = param_info.get('type', 'string')
                        param_desc = param_info.get('description', 'No description')
                        required = param_name in selected_tool.parameters.get('required', [])
                        
                        print(f"  {param_name} ({param_type}){' [REQUIRED]' if required else ''}: {param_desc}")
                        
                        if required or input(f"Enter value for {param_name} (or press Enter to skip): ").strip():
                            value = input(f"Value for {param_name}: ").strip()
                            if value:
                                # Simple type conversion
                                if param_type == 'integer':
                                    try:
                                        arguments[param_name] = int(value)
                                    except ValueError:
                                        print(f"Warning: Could not convert '{value}' to integer")
                                        arguments[param_name] = value
                                elif param_type == 'boolean':
                                    arguments[param_name] = value.lower() in ('true', '1', 'yes', 'on')
                                else:
                                    arguments[param_name] = value
            
            print(f"\nCalling tool '{selected_tool.name}' with arguments: {json.dumps(arguments, indent=2)}")
            
            try:
                result = await client.call_tool(selected_tool.name, arguments)
                print(f"\n✅ Tool call successful!")
                print(f"Result: {json.dumps(result, indent=2)}")
            except Exception as e:
                print(f"\n❌ Error calling tool: {str(e)}")
                
        else:
            print("Invalid selection.")
    except ValueError:
        print("Please enter a valid number.")


async def search_and_call_tools(client: UtcpClient) -> None:
    """Search for tools based on user query and optionally call them."""
    while True:
        query = input("\nEnter search query for Europcar tools (or 'back' to return): ").strip()
        if query.lower() == 'back':
            break
            
        print(f"\nSearching for tools matching: '{query}'...")
        relevant_tools = await client.search_tools(query, limit=10)
        
        if relevant_tools:
            print(f"Found {len(relevant_tools)} relevant tools:")
            display_tools(relevant_tools)
            
            if input("\nWould you like to call one of these tools? (y/n): ").lower() == 'y':
                await interactive_tool_call(client, relevant_tools)
        else:
            print("No relevant tools found for your query.")


async def main():
    """Main function to demonstrate Europcar API integration."""
    load_dotenv(Path(__file__).parent / ".env")
    
    print("🚗 Europcar API UTCP Integration Example")
    print("=" * 45)
    
    print("\nInitializing UTCP client...")
    try:
        utcp_client = await initialize_utcp_client()
        print("✅ UTCP client initialized successfully.")
        
        # Check if any tools were actually discovered
        all_tools = await utcp_client.tool_repository.get_tools()
        if not all_tools:
            print("\n⚠️  WARNING: No tools discovered from the API!")
            print("This usually means:")
            print("  1. The OpenAPI spec URL is incorrect or returns 404")
            print("  2. The API requires authentication to access the spec")
            print("  3. The API spec has no paths/operations defined")
            print("\n🔧 Debug steps:")
            print("  1. Verify your API is accessible at: https://europcar-api.nuevotest.com/swagger/index.html")
            print("  2. Check the correct swagger.json URL in providers.json")
            print("  3. Add authentication if required")
            print("  4. Use manual tool definition as fallback")
            print("\n📚 See README.md for troubleshooting guide")
            
            if input("\nContinue anyway? (y/n): ").lower() != 'y':
                sys.exit(0)
        else:
            print(f"✅ Found {len(all_tools)} tools from the API")
            
    except Exception as e:
        print(f"❌ Error initializing UTCP client: {str(e)}")
        print("\nTips:")
        print("- Make sure the Europcar API is accessible")
        print("- Check your .env file for correct API credentials")
        print("- Verify the providers.json configuration")
        sys.exit(1)

    while True:
        print("\n" + "=" * 45)
        print("Choose an option:")
        print("1. List all available tools")
        print("2. Search and call specific tools")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            print("\nFetching all available tools from Europcar API...")
            try:
                all_tools = await utcp_client.tool_repository.get_tools()
                display_tools(all_tools)
                
                if all_tools and input("\nWould you like to call one of these tools? (y/n): ").lower() == 'y':
                    await interactive_tool_call(utcp_client, all_tools)
                    
            except Exception as e:
                print(f"❌ Error fetching tools: {str(e)}")
                
        elif choice == "2":
            await search_and_call_tools(utcp_client)
            
        elif choice == "3":
            print("\nGoodbye! 🚗")
            break
            
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")


if __name__ == "__main__":
    asyncio.run(main())
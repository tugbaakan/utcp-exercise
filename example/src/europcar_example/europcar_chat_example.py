"""
UTCP Europcar API Chat Interface Example

This example demonstrates a conversational chat interface for interacting with the Europcar API
through the Universal Tool Calling Protocol (UTCP) framework.

Features:
- Natural language chat interface
- Automatic intent recognition
- Conversational tool discovery and execution
- Interactive parameter collection
- Friendly error handling
"""

import asyncio
import os
import json
import sys
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv

from utcp.client.utcp_client import UtcpClient
from utcp.client.utcp_client_config import UtcpClientConfig, UtcpDotEnv
from utcp.shared.tool import Tool


class EuropcarChatBot:
    """A conversational chat bot for interacting with Europcar API tools."""
    
    def __init__(self, utcp_client: UtcpClient):
        self.client = utcp_client
        self.conversation_history = []
        
    async def initialize(self) -> bool:
        """Initialize the chat bot and check if tools are available."""
        try:
            all_tools = await self.client.tool_repository.get_tools()
            if not all_tools:
                print("🤖 Hi! I'm your Europcar API assistant, but I'm having trouble connecting to the API.")
                print("     This usually means the API spec couldn't be loaded. Check the troubleshooting guide.")
                return False
            else:
                print(f"🤖 Hi! I'm your Europcar API assistant. I have access to {len(all_tools)} tools from the Europcar API.")
                print("     You can ask me to search for cars, make reservations, check locations, and much more!")
                print("\n     Try saying things like:")
                print("     • 'Show me all available tools'")
                print("     • 'Search for car reservation tools'")
                print("     • 'Help me find a car in Istanbul'")
                print("     • 'What can you do?'")
                print("     • 'Exit' or 'quit' to leave")
                return True
        except Exception as e:
            print(f"🤖 Sorry, I encountered an error while initializing: {str(e)}")
            return False
    
    def parse_intent(self, user_input: str) -> Dict[str, Any]:
        """Parse user input to determine intent and extract relevant information."""
        user_input = user_input.lower().strip()
        
        # Exit intents
        if any(word in user_input for word in ['exit', 'quit', 'bye', 'goodbye']):
            return {'intent': 'exit'}
        
        # Help intents
        if any(word in user_input for word in ['help', 'what can you do', 'capabilities', 'what do you do']):
            return {'intent': 'help'}
        
        # List all tools
        if any(phrase in user_input for phrase in ['show all', 'list all', 'all tools', 'everything']):
            return {'intent': 'list_all_tools'}
        
        # Direct tool execution with parameters (e.g., "search stations near airport")
        station_patterns = [
            r'search stations? (?:near |in |at |for )?(.+)',
            r'find stations? (?:near |in |at |for )?(.+)',
            r'stations? (?:near |in |at |for )?(.+)',
        ]
        
        for pattern in station_patterns:
            match = re.search(pattern, user_input)
            if match:
                search_term = match.group(1).strip()
                if search_term and search_term not in ['here', 'me', 'there']:
                    return {'intent': 'direct_tool_call', 'tool_search': 'SearchStations', 'parameters': {'searchTerm': search_term}}
        
        # Search for specific tools
        search_patterns = [
            r'search for (.+)',
            r'find (.+)',
            r'look for (.+)',
            r'i need (.+)',
            r'help me (.+)',
            r'show me (.+) tools?',
            r'(.+) tools?',
        ]
        
        for pattern in search_patterns:
            match = re.search(pattern, user_input)
            if match:
                query = match.group(1).strip()
                # Filter out common words that aren't useful for search
                if query not in ['tools', 'something', 'anything', 'help']:
                    return {'intent': 'search_tools', 'query': query}
        
        # Default to search if we can't parse intent but have meaningful content
        if len(user_input.split()) > 1:
            return {'intent': 'search_tools', 'query': user_input}
        
        return {'intent': 'unknown', 'original_input': user_input}
    
    async def handle_chat_message(self, user_input: str) -> bool:
        """Handle a chat message and return False if user wants to exit."""
        intent_data = self.parse_intent(user_input)
        intent = intent_data.get('intent')
        
        if intent == 'exit':
            print("\n🤖 Thanks for using the Europcar API assistant! Have a great day! 🚗")
            return False
        
        elif intent == 'help':
            await self.show_help()
        
        elif intent == 'list_all_tools':
            await self.list_all_tools()
        
        elif intent == 'search_tools':
            query = intent_data.get('query', '')
            await self.search_and_suggest_tools(query)
        
        elif intent == 'direct_tool_call':
            # Handle direct tool calls with extracted parameters
            tool_search = intent_data.get('tool_search', '')
            parameters = intent_data.get('parameters', {})
            await self.execute_direct_tool_call(tool_search, parameters)
        
        elif intent == 'unknown':
            await self.handle_unknown_input(intent_data.get('original_input', ''))
        
        return True
    
    async def show_help(self):
        """Show help information."""
        print("\n🤖 I'm here to help you interact with the Europcar API! Here's what I can do:")
        print("\n   🔍 Tool Discovery:")
        print("     • 'Show me all tools' - List every available API endpoint")
        print("     • 'Search for reservations' - Find tools related to reservations")
        print("     • 'Find car search tools' - Look for car availability tools")
        print("\n   🚗 Car Rental Tasks:")
        print("     • 'Help me find a car' - Search for available vehicles")
        print("     • 'I need to make a reservation' - Find booking tools")
        print("     • 'Search stations near airport' - Find stations by location")
        print("     • 'Find stations in Istanbul' - Search for city stations")
        print("\n   💬 Chat Tips:")
        print("     • Be specific about what you want to do")
        print("     • I'll suggest relevant tools and help you use them")
        print("     • Say 'exit' or 'quit' when you're done")
    
    async def list_all_tools(self):
        """List all available tools in a conversational way."""
        print("\n🤖 Let me show you all the tools I have access to...")
        try:
            all_tools = await self.client.tool_repository.get_tools()
            if all_tools:
                print(f"\n   I found {len(all_tools)} tools from the Europcar API:")
                print("   " + "=" * 50)
                
                # Group tools by category for better organization
                categories = {}
                for tool in all_tools:
                    # Extract category from tool name or use a default
                    parts = tool.name.split('_')
                    category = parts[0].title() if parts else "General"
                    if category not in categories:
                        categories[category] = []
                    categories[category].append(tool)
                
                for category, tools in categories.items():
                    print(f"\n   📂 {category} ({len(tools)} tools):")
                    for tool in tools[:5]:  # Show first 5 tools in each category
                        print(f"     • {tool.name}")
                        if tool.description:
                            print(f"       {tool.description[:80]}...")
                    if len(tools) > 5:
                        print(f"     ... and {len(tools) - 5} more")
                
                print(f"\n🤖 That's a lot of tools! You can search for specific ones by telling me what you want to do.")
                print("   For example: 'Find reservation tools' or 'Search for car availability'")
            else:
                print("\n🤖 Hmm, I don't see any tools available right now. There might be a connection issue.")
        except Exception as e:
            print(f"\n🤖 Sorry, I had trouble fetching the tools: {str(e)}")
    
    async def search_and_suggest_tools(self, query: str):
        """Search for tools and suggest them conversationally."""
        print(f"\n🤖 Looking for tools related to '{query}'...")
        try:
            relevant_tools = await self.client.search_tools(query, limit=10)
            
            if relevant_tools:
                print(f"\n   Great! I found {len(relevant_tools)} tools that might help:")
                print("   " + "-" * 40)
                
                for i, tool in enumerate(relevant_tools, 1):
                    print(f"\n   {i}. {tool.name}")
                    if tool.description:
                        print(f"      {tool.description}")
                    if hasattr(tool, 'parameters') and tool.parameters:
                        params = list(tool.parameters.get('properties', {}).keys())
                        if params:
                            print(f"      Parameters: {', '.join(params[:3])}{'...' if len(params) > 3 else ''}")
                
                print(f"\n🤖 Would you like me to help you use one of these tools? Just tell me the number!")
                print("   Or you can ask me to search for something else.")
                
                # Wait for user response
                response = input("\n💬 Your choice: ").strip()
                await self.handle_tool_selection(response, relevant_tools)
                
            else:
                print(f"\n🤖 I couldn't find any tools matching '{query}'. Let me suggest some alternatives:")
                print("   • Try broader terms like 'car', 'reservation', 'location'")
                print("   • Say 'show me all tools' to see everything available")
                print("   • Ask 'what can you do?' for more ideas")
        except Exception as e:
            print(f"\n🤖 Sorry, I had trouble searching for tools: {str(e)}")
    
    async def handle_tool_selection(self, response: str, tools: List[Tool]):
        """Handle user selection of a tool from search results."""
        try:
            # Try to parse as a number
            tool_index = int(response) - 1
            if 0 <= tool_index < len(tools):
                selected_tool = tools[tool_index]
                await self.execute_tool_conversationally(selected_tool)
            else:
                print(f"\n🤖 Please choose a number between 1 and {len(tools)}, or tell me what else you'd like to do.")
        except ValueError:
            # If not a number, treat as a new chat message
            if response.strip():
                print(f"\n🤖 Got it! Let me help you with: '{response}'")
                await self.handle_chat_message(response)
    
    async def execute_tool_conversationally(self, tool: Tool, pre_filled_params: Optional[Dict[str, Any]] = None):
        """Execute a tool with conversational parameter collection."""
        print(f"\n🤖 Great choice! Let's use the '{tool.name}' tool.")
        if tool.description:
            print(f"   This tool: {tool.description}")
        
        arguments = pre_filled_params.copy() if pre_filled_params else {}
        
        # Collect parameters conversationally
        if hasattr(tool, 'inputs') and tool.inputs:
            # Use the inputs schema which is more reliable
            properties = getattr(tool.inputs, 'properties', {}) if hasattr(tool.inputs, 'properties') else {}
            required_params = getattr(tool.inputs, 'required', []) if hasattr(tool.inputs, 'required') else []
            
            if properties:
                if not pre_filled_params:
                    print(f"\n   I need some information to use this tool:")
                else:
                    print(f"\n   I've pre-filled some parameters, but let me check if you need to provide more:")
                
                for param_name, param_info in properties.items():
                    # Skip if already provided
                    if param_name in arguments:
                        print(f"   ✅ {param_name}: {arguments[param_name]}")
                        continue
                        
                    param_type = param_info.get('type', 'string')
                    param_desc = param_info.get('description', 'No description available')
                    is_required = param_name in required_params
                    
                    # Special handling for station search - searchTerm is effectively required
                    if 'SearchStations' in tool.name and param_name == 'searchTerm':
                        is_required = True
                        param_desc = "Search term for finding stations (e.g., 'airport', 'istanbul', 'center')"
                    
                    # Make the prompt conversational
                    if is_required:
                        prompt = f"\n   ✨ {param_name} (required): {param_desc}\n      Please enter: "
                    else:
                        prompt = f"\n   🔧 {param_name} (optional): {param_desc}\n      Enter value or press Enter to skip: "
                    
                    value = input(prompt).strip()
                    
                    if value:
                        # Type conversion with friendly error handling
                        try:
                            if param_type == 'integer':
                                arguments[param_name] = int(value)
                            elif param_type == 'boolean':
                                arguments[param_name] = value.lower() in ('true', '1', 'yes', 'on')
                            else:
                                arguments[param_name] = value
                        except ValueError:
                            print(f"      (Using '{value}' as-is)")
                            arguments[param_name] = value
                    elif is_required:
                        print(f"      ⚠️  This parameter is required. Using empty value.")
                        arguments[param_name] = ""
        
        # Execute the tool
        print(f"\n🤖 Alright, calling the '{tool.name}' tool...")
        if arguments:
            print(f"   Using parameters: {json.dumps(arguments, indent=2)}")
        
        try:
            result = await self.client.call_tool(tool.name, arguments)
            print(f"\n✅ Success! Here's what I got back:")
            
            # Pretty print results for station searches
            if 'SearchStations' in tool.name and isinstance(result, dict):
                data = result.get('data', [])
                if data and isinstance(data, list):
                    print(f"   Found {len(data)} station groups:")
                    for i, group in enumerate(data[:5], 1):  # Show first 5 groups
                        if isinstance(group, dict):
                            group_name = group.get('groupName', 'Unknown Group')
                            stations = group.get('stations', [])
                            print(f"   {i}. {group_name} ({len(stations)} stations)")
                    if len(data) > 5:
                        print(f"   ... and {len(data) - 5} more groups")
                else:
                    print(f"   No stations found for your search term.")
            else:
                print(f"   {json.dumps(result, indent=2)}")
            
            print(f"\n🤖 Is there anything else I can help you with?")
        except Exception as e:
            print(f"\n❌ Oops! Something went wrong: {str(e)}")
            print(f"🤖 Don't worry, you can try again or ask me to search for different tools.")
    
    async def execute_direct_tool_call(self, tool_search: str, parameters: Dict[str, Any]):
        """Execute a tool directly with pre-extracted parameters."""
        print(f"\n🤖 I understand you want to search for stations. Let me find the right tool for you...")
        
        # For station searches, look specifically for SearchStations tool
        if 'SearchStations' in tool_search:
            all_tools = await self.client.tool_repository.get_tools()
            search_stations_tool = None
            
            for tool in all_tools:
                if 'SearchStations' in tool.name:
                    search_stations_tool = tool
                    break
            
            if search_stations_tool:
                print(f"   Found the perfect tool: {search_stations_tool.name}")
                
                # Execute with pre-filled parameters - SearchStations doesn't need interactive parameter collection
                print(f"\n🤖 Great! I'll search for stations matching '{parameters.get('searchTerm', '')}'...")
                
                try:
                    result = await self.client.call_tool(search_stations_tool.name, parameters)
                    print(f"\n✅ Success! Here's what I found:")
                    
                    # Pretty print results for station searches
                    if isinstance(result, dict):
                        data = result.get('data', [])
                        if data and isinstance(data, list):
                            print(f"   Found {len(data)} station groups matching '{parameters.get('searchTerm', '')}':")
                            for i, group in enumerate(data[:10], 1):  # Show first 10 groups
                                if isinstance(group, dict):
                                    group_name = group.get('groupName', 'Unknown Group')
                                    stations = group.get('stations', [])
                                    print(f"   {i}. {group_name} ({len(stations)} stations)")
                                    # Show first few stations in each group
                                    for j, station in enumerate(stations[:3], 1):
                                        if isinstance(station, dict):
                                            station_name = station.get('name', 'Unknown Station')
                                            city = station.get('city', '')
                                            print(f"      • {station_name}" + (f" - {city}" if city else ""))
                                    if len(stations) > 3:
                                        print(f"      ... and {len(stations) - 3} more stations")
                            if len(data) > 10:
                                print(f"   ... and {len(data) - 10} more groups")
                        else:
                            print(f"   No stations found matching '{parameters.get('searchTerm', '')}'.")
                            print("   Try a different search term like 'airport', 'istanbul', or 'center'.")
                    
                    print(f"\n🤖 Is there anything else I can help you with?")
                except Exception as e:
                    print(f"\n❌ Oops! Something went wrong: {str(e)}")
                    print(f"🤖 Don't worry, you can try a different search term or ask me to search for other tools.")
            else:
                print(f"\n🤖 I couldn't find the SearchStations tool. Let me show you what's available...")
                await self.search_and_suggest_tools('station')
        else:
            # Fallback for other tool searches
            relevant_tools = await self.client.search_tools(tool_search, limit=5)
            
            if relevant_tools:
                # Use the first matching tool
                selected_tool = relevant_tools[0]
                print(f"   Found the perfect tool: {selected_tool.name}")
                
                # Execute with pre-filled parameters
                await self.execute_tool_conversationally(selected_tool, parameters)
            else:
                print(f"\n🤖 I couldn't find a tool for '{tool_search}'. Let me show you what's available...")
                await self.search_and_suggest_tools(tool_search)
    
    async def handle_unknown_input(self, user_input: str):
        """Handle input that couldn't be parsed."""
        print(f"\n🤖 I'm not sure what you'd like to do with '{user_input}'.")
        print("   Here are some things you can try:")
        print("   • 'Show me all tools' - See everything available")
        print("   • 'Search for [what you need]' - Find specific tools")
        print("   • 'Help' - Get more guidance")
        print("   • Or just tell me what you want to accomplish!")


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
    """Main chat interface function."""
    load_dotenv(Path(__file__).parent / ".env")
    
    print("🚗 Europcar API Chat Assistant")
    print("=" * 35)
    print("Starting up...")
    
    try:
        # Initialize UTCP client
        utcp_client = await initialize_utcp_client()
        
        # Create chat bot
        chat_bot = EuropcarChatBot(utcp_client)
        
        # Initialize and check if ready
        if not await chat_bot.initialize():
            print("\n🤖 I'm having trouble connecting to the API. Check the README for troubleshooting tips.")
            return
        
        # Main chat loop
        print("\n" + "=" * 50)
        while True:
            user_input = input("\n💬 You: ").strip()
            
            if not user_input:
                print("🤖 I'm here when you need me! Just tell me what you'd like to do.")
                continue
            
            # Handle the message and check if user wants to exit
            should_continue = await chat_bot.handle_chat_message(user_input)
            if not should_continue:
                break
    
    except KeyboardInterrupt:
        print("\n\n🤖 Chat interrupted. Thanks for using the Europcar API assistant!")
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
        print("🤖 Please check your configuration and try again.")


if __name__ == "__main__":
    asyncio.run(main())
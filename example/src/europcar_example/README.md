# Europcar API UTCP Integration Example

This example demonstrates how to integrate the Europcar API with the Universal Tool Calling Protocol (UTCP) framework.

## 🚗 What This Example Does

- **Automatic Tool Discovery**: Connects to your Europcar API and automatically discovers available endpoints as callable tools
- **Interactive Tool Calling**: Provides a user-friendly interface to search, select, and execute API calls
- **Error Handling**: Gracefully handles API errors and provides helpful feedback
- **Type Safety**: Automatically handles parameter types and validation

## 📋 Prerequisites

1. Python 3.8+
2. Access to the Europcar API at `https://europcar-api.nuevotest.com`
3. API credentials (if required by your API)

## 🛠️ Setup Instructions

### 1. Install Dependencies

```bash
# From the project root directory
pip install -r requirements.txt
```

### 2. Configure Environment

1. Copy the environment template:
   ```bash
   cp example.env .env
   ```

2. **No authentication required!** 
   
   Your Europcar API integration is configured to work without authentication. The system uses a modified OpenAPI specification (`europcar_no_auth_swagger.json`) that has all security requirements removed while preserving all 108 API tools.

### 3. Verify API Configuration

The `providers.json` file contains the API endpoint configuration:

```json
[
    {
        "name": "europcar_api",
        "provider_type": "text",
        "file_path": "./europcar_no_auth_swagger.json"
    }
]
```

**✅ This uses a local OpenAPI spec with authentication removed that provides 108 real API tools!**

### Key Files:
- **`europcar_no_auth_swagger.json`**: Modified OpenAPI spec without security requirements
- **`providers.json`**: UTCP provider configuration pointing to the local spec
- **`UPDATE_GUIDE.md`**: Step-by-step guide for updating the swagger file when the API changes

## 🚀 Running the Example

### Menu-Driven Interface (Original)
```bash
cd example/src/europcar_example
python europcar_utcp_example.py
```

### Chat Interface (New!)
For a more conversational experience:
```bash
cd example/src/europcar_example  
python europcar_chat_example.py
```

The chat interface allows you to interact naturally:
- **"Show me all tools"** - List available API endpoints
- **"Search for car reservations"** - Find relevant tools  
- **"Search stations near airport"** - Find stations by location with smart parameter extraction
- **"Find stations in Istanbul"** - Natural language station search
- **"What can you do?"** - Get help and examples

## 💡 Usage Examples

### Interactive Menu
The example provides an interactive menu with options to:

1. **List All Tools**: See all available API endpoints
2. **Search Tools**: Find specific endpoints by description or functionality
3. **Execute Tools**: Call API endpoints with proper parameters

### Sample Workflow

```
🚗 Europcar API UTCP Integration Example
=============================================

✅ UTCP client initialized successfully.

Choose an option:
1. List all available tools
2. Search and call specific tools  
3. Exit

Enter your choice (1-3): 2

Enter search query for Europcar tools: car reservation

Found 3 relevant tools:
--------------------------------------------------
1. create_reservation
   Description: Create a new car reservation
   Method: POST
   Parameters: ['pickup_location', 'return_location', 'pickup_date', 'return_date', 'car_type']

2. get_reservation
   Description: Retrieve reservation details
   Method: GET
   Parameters: ['reservation_id']

3. cancel_reservation
   Description: Cancel an existing reservation
   Method: DELETE
   Parameters: ['reservation_id']
```

## 🔧 Customization

### Adding Authentication
If your API requires authentication, update the `.env` file with the appropriate credentials and modify the `providers.json` if needed.

### Custom Parameters
The example automatically discovers parameters from your OpenAPI specification. You can customize parameter handling in the `interactive_tool_call` function.

### Error Handling
Add custom error handling for specific API responses in the tool calling section.

## 🐛 Troubleshooting

### Common Issues

1. **"No relevant tools found for your query"**: 
   - **Root Cause**: The OpenAPI spec URL returns 404 or empty content
   - **Solutions**:
     - Try different swagger URLs in `providers.json`:
       ```json
       "url": "https://europcar-api.nuevotest.com/swagger.json"
       "url": "https://europcar-api.nuevotest.com/api-docs"
       "url": "https://europcar-api.nuevotest.com/openapi.json"
       ```
     - Use the manual fallback configuration:
       ```bash
       cp providers_manual_fallback.json providers.json
       ```
     - Add authentication headers if required

2. **"No tools discovered from the API"**:
   - Check if the swagger endpoint exists: visit your [Swagger UI](https://europcar-api.nuevotest.com/swagger/index.html)
   - Verify the correct JSON spec URL (look for network requests in browser dev tools)
   - Ensure the API spec has `paths` defined with actual endpoints

3. **Authentication errors**:
   - **Not applicable** - This integration runs without authentication
   - If you see auth errors, ensure you're using the modified `europcar_no_auth_swagger.json` spec

4. **Connection timeouts**:
   - Increase the `EUROPCAR_REQUEST_TIMEOUT` value in `.env`
   - Check your network connection to the API

### Debug Mode
Enable debug mode in your `.env` file:
```
DEBUG=true
```

This will provide verbose logging to help diagnose issues.

### Alternative Configurations

1. **Manual Tool Configuration** (if needed):
   ```bash
   cp providers_manual_fallback.json providers.json
   ```

2. **Original API with Authentication** (if you have credentials):
   ```bash
   # Use the original spec that requires authentication
   # Update providers.json to point to the original endpoint
   ```

### Finding the Correct OpenAPI Spec URL

1. Visit your Swagger UI: [https://europcar-api.nuevotest.com/swagger/index.html](https://europcar-api.nuevotest.com/swagger/index.html)
2. Open browser developer tools (F12)
3. Look for network requests to find the actual JSON spec URL
4. Update the `url` field in `providers.json` with the correct endpoint

## 📚 API Documentation

Your API documentation is available at: [https://europcar-api.nuevotest.com/swagger/index.html](https://europcar-api.nuevotest.com/swagger/index.html)

## 🤝 Contributing

Feel free to enhance this example by:
- Adding more sophisticated error handling
- Implementing caching for frequently called endpoints
- Adding data validation and transformation
- Creating specialized workflows for common use cases
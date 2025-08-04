import google.generativeai as genai
from rich.console import Console
from rich.markdown import Markdown
from config.settings import config
from tools import file_system, mysql_tools, system, web_fetcher
from tools.memory_manager import MemoryManager

class GeminiAgent:
    def __init__(self):
        self.console = Console()
        self.model = self._setup_model()
        self.history = []
        self.memory = MemoryManager()
        self.tools = self._setup_tools()
        self.function_map = self._setup_function_map()

    def _setup_model(self):
        genai.configure(api_key=config.GEMINI_API_KEY)
        return genai.GenerativeModel(config.MODEL_NAME)

    def _setup_tools(self):
        return [
            genai.protos.Tool(
                function_declarations=[
                    # file func declaration
                    genai.protos.FunctionDeclaration(
                        name="check_trash_bin",
                        description="Check Trash/Recycle Bin for files older than specified days",
                        parameters=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={
                                "days_threshold": genai.protos.Schema(
                                    type=genai.protos.Type.INTEGER,
                                    description="Only show files older than this many days (default: 10)"
                                )
                            }
                        )
                    ),
                    genai.protos.FunctionDeclaration(
                        name="clean_old_trash_files",
                        description="Delete files from trash older than specified days",
                        parameters=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={
                                "days_threshold": genai.protos.Schema(
                                    type=genai.protos.Type.INTEGER,
                                    description="Delete files older than this many days"
                                ),
                                "confirm": genai.protos.Schema(
                                    type=genai.protos.Type.BOOLEAN,
                                    description="Whether to ask for confirmation (default: true)"
                                )
                            },
                            required=["days_threshold"]
                        )
                    ),
                    genai.protos.FunctionDeclaration(
                        name="read_file_content",
                        description="Read and analyze the content of a file",
                        parameters=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={
                                "file_path": genai.protos.Schema(
                                    type=genai.protos.Type.STRING,
                                    description="Path to the file to read (supports ~ for home directory)"
                                ),
                                "max_lines": genai.protos.Schema(
                                    type=genai.protos.Type.INTEGER,
                                    description="Maximum number of lines to read (default: 500)"
                                )
                            },
                            required=["file_path"]
                        )
                    ),
                    genai.protos.FunctionDeclaration(
                        name="write_file_content",
                        description="Write content to a file with optional backup",
                        parameters=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={
                                "file_path": genai.protos.Schema(
                                    type=genai.protos.Type.STRING,
                                    description="Path where to write the file"
                                ),
                                "content": genai.protos.Schema(
                                    type=genai.protos.Type.STRING,
                                    description="Content to write to the file"
                                ),
                                "backup": genai.protos.Schema(
                                    type=genai.protos.Type.BOOLEAN,
                                    description="Create backup of existing file (default: true)"
                                )
                            },
                            required=["file_path", "content"]
                        )
                    ),
                    genai.protos.FunctionDeclaration(
                        name="list_directory_contents",
                        description="List files and directories in a given path",
                        parameters=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={
                                "dir_path": genai.protos.Schema(
                                    type=genai.protos.Type.STRING,
                                    description="Directory path to list (default: current directory)"
                                ),
                                "show_hidden": genai.protos.Schema(
                                    type=genai.protos.Type.BOOLEAN,
                                    description="Show hidden files starting with . (default: false)"
                                )
                            }
                        )
                    ),
                    genai.protos.FunctionDeclaration(
                        name="find_files",
                        description="Find files matching a glob pattern recursively.",
                        parameters=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={
                                "pattern": genai.protos.Schema(
                                    type=genai.protos.Type.STRING,
                                    description="The glob pattern to match (e.g., '**/*.py')"
                                ),
                                "base_path": genai.protos.Schema(
                                    type=genai.protos.Type.STRING,
                                    description="The base path to search from (default: current directory)"
                                )
                            },
                            required=["pattern"]
                        )
                    ),
                    genai.protos.FunctionDeclaration(
                        name="search_text",
                        description="Search for a text pattern in files matching a glob pattern.",
                        parameters=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={
                                "pattern": genai.protos.Schema(
                                    type=genai.protos.Type.STRING,
                                    description="The text pattern to search for (can be a regex)."
                                ),
                                "file_pattern": genai.protos.Schema(
                                    type=genai.protos.Type.STRING,
                                    description="The glob pattern for files to search (e.g., '**/*.py')."
                                ),
                                "base_path": genai.protos.Schema(
                                    type=genai.protos.Type.STRING,
                                    description="The base path to search from (default: current directory)."
                                )
                            },
                            required=["pattern", "file_pattern"]
                        )
                    ),
                    # sqldb Tools
                    genai.protos.FunctionDeclaration(
                        name="create_mysql_database",
                        description="Create a new MySQL database with metadata tracking",
                        parameters=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={
                                "database_name": genai.protos.Schema(
                                    type=genai.protos.Type.STRING,
                                    description="Name of the MySQL database to create"
                                ),
                                "description": genai.protos.Schema(
                                    type=genai.protos.Type.STRING,
                                    description="Description of the database purpose"
                                )
                            },
                            required=["database_name"]
                        )
                    ),
                    genai.protos.FunctionDeclaration(
                        name="execute_mysql_command",
                        description="Execute SQL commands on MySQL database and save to .sql file",
                        parameters=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={
                                "database_name": genai.protos.Schema(
                                    type=genai.protos.Type.STRING,
                                    description="Name of the MySQL database"
                                ),
                                "sql_command": genai.protos.Schema(
                                    type=genai.protos.Type.STRING,
                                    description="SQL command(s) to execute"
                                ),
                                "save_to_file": genai.protos.Schema(
                                    type=genai.protos.Type.BOOLEAN,
                                    description="Whether to save commands to .sql file (default: true)"
                                )
                            },
                            required=["database_name", "sql_command"]
                        )
                    ),
                    genai.protos.FunctionDeclaration(
                        name="analyze_mysql_database_structure",
                        description="Analyze MySQL database structure and provide educational insights about normalization",
                        parameters=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={
                                "database_name": genai.protos.Schema(
                                    type=genai.protos.Type.STRING,
                                    description="Name of the MySQL database to analyze"
                                )
                            },
                            required=["database_name"]
                        )
                    ),
                    genai.protos.FunctionDeclaration(
                        name="list_mysql_databases",
                        description="List all MySQL databases with metadata",
                        parameters=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={}
                        )
                    ),
                    # System Tools
                    genai.protos.FunctionDeclaration(
                        name="get_system_info",
                        description="Get current system information including platform, resources, and user details",
                        parameters=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={}
                        )
                    ),
                    genai.protos.FunctionDeclaration(
                        name="run_python_script",
                        description="Execute a Python script and capture output and errors",
                        parameters=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={
                                "script_path": genai.protos.Schema(
                                    type=genai.protos.Type.STRING,
                                    description="Path to the Python script to execute"
                                ),
                                "timeout": genai.protos.Schema(
                                    type=genai.protos.Type.INTEGER,
                                    description="Maximum execution time in seconds (default: 30)"
                                )
                            },
                            required=["script_path"]
                        )
                    ),
                    genai.protos.FunctionDeclaration(
                        name="analyze_python_code",
                        description="Analyze Python code for syntax errors, issues, and suggestions",
                        parameters=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={
                                "file_path": genai.protos.Schema(
                                    type=genai.protos.Type.STRING,
                                    description="Path to the Python file to analyze"
                                )
                            },
                            required=["file_path"]
                        )
                    ),
                    genai.protos.FunctionDeclaration(
                        name="send_system_notification",
                        description="Send a system notification (macOS)",
                        parameters=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={
                                "message": genai.protos.Schema(
                                    type=genai.protos.Type.STRING,
                                    description="Notification message content"
                                ),
                                "title": genai.protos.Schema(
                                    type=genai.protos.Type.STRING,
                                    description="Notification title (default: 'System Agent')"
                                )
                            },
                            required=["message"]
                        )
                    ),
                    genai.protos.FunctionDeclaration(
                        name="execute_cli_command",
                        description="Execute CLI command with proper shell handling",
                        parameters=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={
                                "command": genai.protos.Schema(
                                    type=genai.protos.Type.STRING,
                                    description="The command to execute"
                                ),
                                "timeout": genai.protos.Schema(
                                    type=genai.protos.Type.INTEGER,
                                    description="Maximum execution time in seconds (default: 30)"
                                )
                            },
                            required=["command"]
                        )
                    ),
                    # Web Functions
                    genai.protos.FunctionDeclaration(
                        name="fetch_url_content",
                        description="Fetches and returns the text content of a given URL.",
                        parameters=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={
                                "url": genai.protos.Schema(
                                    type=genai.protos.Type.STRING,
                                    description="The URL to fetch content from."
                                )
                            },
                            required=["url"]
                        )
                    ),
                    # Memory Tool
                    genai.protos.FunctionDeclaration(
                        name="remember_fact",
                        description="Saves a fact to the agent's long-term memory.",
                        parameters=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={
                                "fact": genai.protos.Schema(
                                    type=genai.protos.Type.STRING,
                                    description="The fact to be remembered."
                                )
                            },
                            required=["fact"]
                        )
                    ),
                    genai.protos.FunctionDeclaration( 
                        name="forget",
                        description="Searches for and optionally removes semantically similar memories from the agent's long-term memory.",
                        parameters=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={
                                "fact": genai.protos.Schema(
                                    type=genai.protos.Type.STRING,
                                    description="The fact to forget; similar memories will be searched based on this input."
                                ),
                                "confirm": genai.protos.Schema(
                                    type=genai.protos.Type.BOOLEAN,
                                    description="If true, confirms and deletes matched memories. If false, just previews matches."
                                ),
                                "similarity_threshold": genai.protos.Schema(
                                    type=genai.protos.Type.NUMBER,
                                    description="Optional similarity threshold (0.0 - 1.0) for matching memories (default: 0.85)."
                                ),
                                "top_n": genai.protos.Schema(
                                    type=genai.protos.Type.INTEGER,
                                    description="Optional number of top similar memories to consider for deletion (default: 3)."
                                )
                            },
                            required=["fact"]
                        )
                    ) 
                ]
            )
        ]

    def _setup_function_map(self):
        return {
            # File System Tools
            "check_trash_bin": file_system.check_trash_bin,
            "clean_old_trash_files": file_system.clean_old_trash_files,
            "read_file_content": file_system.read_file_content,
            "write_file_content": file_system.write_file_content,
            "list_directory_contents": file_system.list_directory_contents,
            "find_files": file_system.find_files,
            "search_text": file_system.search_text,
            # mysql db Tools
            "create_mysql_database": mysql_tools.create_mysql_database,
            "execute_mysql_command": mysql_tools.execute_mysql_command,
            "analyze_mysql_database_structure": mysql_tools.analyze_mysql_database_structure,
            "list_mysql_databases": mysql_tools.list_mysql_databases,
            # System Tools
            "get_system_info": system.get_system_info,
            "run_python_script": system.run_python_script,
            "analyze_python_code": system.analyze_python_code,
            "send_system_notification": system.send_system_notification,
            "execute_cli_command": system.execute_cli_command,
            # Web Tool
            "fetch_url_content": web_fetcher.fetch_url_content,
            # Memory Tool
            "remember_fact": self.memory.remember,
            "forget": self.memory.forget
        }

    def execute_function_call(self, function_call):
        function_name = function_call.name
        function_args = dict(function_call.args)

        self.console.print(f"[bold]System Agent executing: {function_name}[/bold]")
        self.console.print(f"[dim]Parameters: {function_args}[/dim]")

        if function_name in self.function_map:
            try:
                result = self.function_map[function_name](**function_args)
                return result
            except Exception as e:
                return {"error": f"Function execution error: {str(e)}"}
        else:
            return {"error": f"Unknown function: {function_name}"}

    def run(self):
        self.console.print("[bold cyan]AICOOK - Your Personal AI Assistant[/bold cyan]")
        self.history.append({"role": "user", "parts": ["You are an AI assistant with memory capabilities."]})
        self.history.append({"role": "model", "parts": ["I am AICOOK, your personal AI assistant. I can learn from our interactions. How can I help you today?"]})
        
        while True:
            try:
                user_input = self.console.input("\n[bold blue]You:[/bold blue] ")

                if user_input.lower() in ['quit', 'exit', 'bye']:
                    self.console.print("\n[yellow]AICOOK shutting down safely. Goodbye![/yellow]")
                    break

                if not user_input.strip():
                    continue

                # remember when needed..
                recalled_memories = self.memory.recall(user_input)
                if recalled_memories:
                    memory_context = "\n".join(recalled_memories)
                    self.history.append({"role": "user", "parts": [f"Relevant memories:\n{memory_context}"]})

                self.history.append({"role": "user", "parts": [user_input]})
                self.console.print("\n[bold green]AICOOK processing...[/bold green]")

                # Iterate through all the responses until no function calls are left
                # max_iterations = 10
                iteration = 0

                while iteration < config.MAX_ITERATIONS:
                    iteration += 1

                    response = self.model.generate_content(self.history, tools=self.tools)
                    has_function_calls = False
                    response_part = response.candidates[0].content.parts
                    if response_part:
                        for part in response_part:
                            if hasattr(part, 'function_call') and part.function_call:
                                has_function_calls = True
                                self.console.print(f"[dim]Operation {iteration}: System function execution...[/dim]")

                                function_result = self.execute_function_call(part.function_call)

                                self.history.append({"role": "model", "parts": [part]})
                                self.history.append({
                                    "role": "function",
                                    "parts": [
                                        genai.protos.Part(
                                            function_response=genai.protos.FunctionResponse(
                                                name=part.function_call.name,
                                                response={"result": function_result}
                                            )
                                        )
                                    ]
                                })

                            elif hasattr(part, 'text') and part.text:
                                self.console.print(f"\n[bold green] System Agent:[/bold green]")
                                self.console.print(Markdown(part.text))
                                self.history.append({"role": "model", "parts": [part.text]})

                    if not has_function_calls:
                        break

                if iteration >= config.MAX_ITERATIONS:
                    self.console.print("\n[yellow] System Agent reached operation limit[/yellow]")

            except KeyboardInterrupt:
                self.console.print("\n[yellow] System Agent interrupted safely. Goodbye![/yellow]")
                break
            except Exception as e:
                self.console.print(f"\n[red]System Agent error: {str(e)}[/red]")
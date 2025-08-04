
import getpass
import mysql.connector
from mysql.connector import Error
from typing import Dict, Any
from datetime import datetime
from pathlib import Path

def prompt_for_mysql_credentials() -> Dict[str, str]:
    """
    Prompts a user for the sql credentials, Handles all the inputs gracefully
    """
    try:
        print("[yellow]🔐 MySQL Authentication Required[/yellow]")

        host = input("MySQL Host [localhost]: ") or "localhost"
        port = input("MySQL Port [3306]: ") or "3306"
        username = input("MySQL Username [root]: ") or "root"
        # Hide the Pass..
        password = getpass.getpass("MySQL Password: ")

        return {
            "host": host,
            "port": int(port),
            "user": username,
            "password": password
        }
    except Exception as e:
        return {"error": f"Failed to get credentials: {str(e)}"}

def create_mysql_database(database_name: str, description: str = "", credentials: Dict[str, str] = None) -> Dict[str, Any]:
    """
    Creates a new MySQL database
    """
    try:
        if not credentials:
            credentials = prompt_for_mysql_credentials()
        if "error" in credentials:
            return credentials

        # Clean database name
        db_name = "".join(c for c in database_name if c.isalnum() or c in ('_')).lower()
        if not db_name:
            return {"error": "Invalid database name"}

        # Connect to the server(mysql)

        connection = mysql.connector.connect(**credentials)
        cursor = connection.cursor()

        # Create database
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        cursor.execute(f"USE {db_name}")

        # Create metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS _database_metadata (
                metadata_key VARCHAR(255) PRIMARY KEY,
                metadata_value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Insert metadata
        cursor.execute("""
            INSERT INTO _database_metadata (metadata_key, metadata_value) 
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE metadata_value = VALUES(metadata_value)
        """, ("database_name", database_name))

        cursor.execute("""
            INSERT INTO _database_metadata (metadata_key, metadata_value) 
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE metadata_value = VALUES(metadata_value)
        """, ("description", description))

        connection.commit()

        # Create SQL file
        sql_file_path = Path(f"{db_name}.sql")
        with open(sql_file_path, 'w') as f:
            f.write(f"-- MySQL Database: {database_name}\n")
            f.write(f"-- Created: {datetime.now().isoformat()}\n")
            f.write(f"-- Description: {description}\n\n")
            f.write(f"CREATE DATABASE IF NOT EXISTS {db_name};\n")
            f.write(f"USE {db_name};\n\n")
            f.write("-- Metadata table\n")
            f.write("""
CREATE TABLE IF NOT EXISTS _database_metadata (
                    metadata_key VARCHAR(255) PRIMARY KEY,
                    metadata_value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
                    """)

        cursor.close()
        connection.close()

        result = {
            "database_name": database_name,
            "mysql_database": db_name,
            "sql_file": str(sql_file_path),
            "description": description,
            "host": credentials["host"],
            "created_at": datetime.now().isoformat(),
            "status": "created"
        }

        return result

    except Error as e:
        return {"error": f"MySQL Error: {str(e)}"}
    except Exception as e:
        return {"error": f"Failed to create MySQL database: {str(e)}"}

def execute_mysql_command(database_name: str, sql_command: str, credentials: Dict[str, str] = None, save_to_file: bool = True) -> Dict[str, Any]:
    """
    run sql command on database
    """
    try:
        if not credentials:
            credentials = prompt_for_mysql_credentials()
        if "error" in credentials:
            return credentials
        db_name = "".join(c for c in database_name if c.isalnum() or c in ('_')).lower()

        # connect to mysql db
        connection = mysql.connector.connect(database=db_name, **credentials)
        cursor = connection.cursor()

        # handle case whereby multiple statements
        commands = [cmd.strip() for cmd in sql_command.split(';') if cmd.strip()]
        results = []

        for cmd in commands:
            try:
                cursor.execute(cmd)

                # Check if it's a SELECT statement
                if cmd.upper().strip().startswith('SELECT'):
                    rows = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    results.append({
                        "command": cmd,
                        "type": "SELECT",
                        "rows": [list(row) for row in rows],
                        "columns": columns,
                        "row_count": len(rows)
                    })
                else:
                    results.append({
                        "command": cmd,
                        "type": cmd.split()[0].upper(),
                        "rows_affected": cursor.rowcount,
                        "success": True
                    })

            except Error as e:
                results.append({
                    "command": cmd,
                    "error": str(e),
                    "success": False
                })

        connection.commit()
        cursor.close()
        connection.close()

        # Save to .sql file if requested
        if save_to_file:
            sql_file_path = Path(f"{db_name}.sql")
            with open(sql_file_path, 'a') as f:
                f.write(f"\n-- Executed: {datetime.now().isoformat()}\n")
                f.write(f"{sql_command};\n")

        result = {
            "database_name": database_name,
            "mysql_database": db_name,
            "commands_executed": len(commands),
            "results": results,
            "execution_time": datetime.now().isoformat(),
            "sql_saved": save_to_file
        }

        return result

    except Error as e:
        return {"error": f"MySQL Error: {str(e)}"}
    except Exception as e:
        return {"error": f"Failed to execute MySQL command: {str(e)}"}

def analyze_mysql_database_structure(database_name: str, credentials: Dict[str, str] = None) -> Dict[str, Any]:
    """
    Analyze MySQL database structure with educational insights
    """
    try:
        if not credentials:
            credentials = prompt_for_mysql_credentials()
        if "error" in credentials:
            return credentials

        db_name = "".join(c for c in database_name if c.isalnum() or c in ('_')).lower()

        # connect] to mysql
        connection = mysql.connector.connect(database=db_name, **credentials)
        cursor = connection.cursor()

        # Get Tables
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall() if table[0] != '_database_metadata']

        table_info = []
        relationships = []

        for table_name in tables:
            # Get table structure
            cursor.execute(f"DESCRIBE {table_name}")
            columns = cursor.fetchall()

            # Get foreign key constraints
            cursor.execute(f"""
                SELECT 
                    COLUMN_NAME,
                    REFERENCED_TABLE_NAME,
                    REFERENCED_COLUMN_NAME
                FROM information_schema.KEY_COLUMN_USAGE 
                WHERE TABLE_SCHEMA = '{db_name}' 
                AND TABLE_NAME = '{table_name}' 
                AND REFERENCED_TABLE_NAME IS NOT NULL
            """)
            foreign_keys = cursor.fetchall()

            # analyse columns
            primary_keys = [col[0] for col in columns if col[3] == 'PRI']
            nullable_columns = [col[0] for col in columns if col[2] == 'YES']

            table_analysis = {
                "table_name": table_name,
                "column_count": len(columns),
                "columns": [{"name": col[0], "type": col[1], "nullable": col[2] == 'YES', "key": col[3]} for col in columns],
                "primary_keys": primary_keys,
                "foreign_keys": [{"column": fk[0], "references_table": fk[1], "references_column": fk[2]} for fk in foreign_keys],
                "nullable_columns": nullable_columns
            }

            table_info.append(table_analysis)

            # gett table relationships
            for fk in foreign_keys:
                relationships.append({
                    "from_table": table_name,
                    "from_column": fk[0],
                    "to_table": fk[1],
                    "to_column": fk[2],
                    "relationship_type": "foreign_key"
                })

        cursor.close()
        connection.close()

        normalization_issues = []
        good_practices = []

        for table in table_info:
            # Check for composite keys
            if len(table["primary_keys"]) > 1:
                good_practices.append(f"Table '{table['table_name']}' uses composite primary key - excellent for junction tables and complex relationships")

            # Check for foreign keys
            if table["foreign_keys"]:
                good_practices.append(f"Table '{table['table_name']}' implements referential integrity through foreign key constraints")

            # Check for potential normalisation issues
            if table["column_count"] > 15:
                normalization_issues.append(f"Table '{table['table_name']}' has many columns ({table['column_count']}) - consider decomposition for better normalization")

        # Determine normalization level
        total_relationships = len(relationships)
        normalization_level = "3NF"
        if total_relationships == 0:
            normalization_level = "1NF"
        elif normalization_issues:
            normalization_level = "2NF"

        educational_analysis = {
            "normalization_level": normalization_level,
            "normalization_explanation": f"This database demonstrates {normalization_level} (Normal Form) principles",
            "design_strengths": good_practices,
            "improvement_suggestions": normalization_issues,
            "relationship_complexity": "High" if total_relationships > 5 else "Medium" if total_relationships > 0 else "Simple",
            "educational_summary": f"Database shows {'excellent' if not normalization_issues else 'good'} design practices with proper table relationships and data integrity constraints."
        }

        result = {
            "database_name": database_name,
            "mysql_database": db_name,
            "total_tables": len(tables),
            "total_relationships": total_relationships,
            "tables": table_info,
            "relationships": relationships,
            "educational_analysis": educational_analysis,
            "analysis_timestamp": datetime.now().isoformat()
        }

        return result

    except Error as e:
        return {"error": f"MySQL Error: {str(e)}"}
    except Exception as e:
        return {"error": f"Failed to analyze MySQL database: {str(e)}"}

def list_mysql_databases(credentials: Dict[str, str] = None) -> Dict[str, Any]:
    """
    List all MySQL databases
    """
    try:
        if not credentials:
            credentials = prompt_for_mysql_credentials()
        if "error" in credentials:
            return credentials

        # Connect to MySQL server
        connection = mysql.connector.connect(**credentials)
        cursor = connection.cursor()

        # Get all databases
        cursor.execute("SHOW DATABASES")
        all_databases = [db[0] for db in cursor.fetchall()]

        # Filter out system databases
        user_databases = [db for db in all_databases if db not in ['information_schema', 'mysql', 'performance_schema', 'sys']]

        database_info = []
        for db_name in user_databases:
            try:
                cursor.execute(f"USE {db_name}")
                cursor.execute("SHOW TABLES")
                table_count = len(cursor.fetchall())

                database_info.append({
                    "database_name": db_name,
                    "table_count": table_count,
                    "has_metadata": False  # Will check if metadata table exists
                })

                # Check for metadata
                cursor.execute("SHOW TABLES LIKE '_database_metadata'")
                if cursor.fetchone():
                    database_info[-1]["has_metadata"] = True
                    cursor.execute("SELECT metadata_key, metadata_value FROM _database_metadata")
                    metadata = dict(cursor.fetchall())
                    database_info[-1]["metadata"] = metadata

            except Error:
                continue

        cursor.close()
        connection.close()

        result = {
            "total_databases": len(database_info),
            "databases": database_info,
            "mysql_host": credentials["host"],
            "scan_timestamp": datetime.now().isoformat()
        }

        return result

    except Error as e:
        return {"error": f"MySQL Error: {str(e)}"}
    except Exception as e:
        return {"error": f"Failed to list MySQL databases: {str(e)}"}

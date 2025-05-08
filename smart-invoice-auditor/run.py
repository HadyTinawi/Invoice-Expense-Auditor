#!/usr/bin/env python3
"""
Smart Invoice Auditor Runner

This script provides a simple command line interface to run different versions
of the Smart Invoice Auditor application.

Usage:
    python run.py [--simple] [--port PORT] [--demo] [--debug]
"""

import argparse
import os
import sys
import subprocess

def main():
    """Parse arguments and run the appropriate version of the application"""
    parser = argparse.ArgumentParser(description="Run Smart Invoice Auditor")
    parser.add_argument("--simple", action="store_true", help="Run the simplified UI version")
    parser.add_argument("--port", type=int, default=7865, help="Port to run the application on")
    parser.add_argument("--demo", action="store_true", help="Run in demo mode")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    args = parser.parse_args()
    
    # Determine which app to run
    if args.simple:
        app_file = "simple_app.py"
        print("Starting Simple Invoice Checker...")
    else:
        app_file = "app.py"
        print("Starting Smart Invoice Auditor...")
    
    # Check if the file exists
    if not os.path.exists(app_file):
        print(f"Error: {app_file} not found in the current directory.")
        return 1
    
    # Prepare command
    cmd = [sys.executable, app_file]
    
    # Modify app.py command for demo mode
    if args.demo and app_file == "app.py":
        print("Running in demo mode...")
        cmd = [sys.executable, "src/main.py", "--demo"]
    
    # Set environment variables for debugging
    env = os.environ.copy()
    if args.debug:
        env["AGENT_VERBOSE"] = "true"
        env["DEBUG"] = "true"
        print("Debug mode enabled.")
    
    # Modify port in script if running app.py or simple_app.py
    if app_file in ["app.py", "simple_app.py"]:
        # Read the file
        with open(app_file, "r") as f:
            content = f.read()
        
        # Find and replace the port
        if "server_port=" in content:
            # Temporarily modify the script with the new port
            temp_file = f"{app_file}.tmp"
            with open(temp_file, "w") as f:
                new_content = content.replace(
                    f"server_port={7863 if '7863' in content else 7865}", 
                    f"server_port={args.port}"
                )
                f.write(new_content)
            
            # Update command to use the temporary file
            cmd[1] = temp_file
            print(f"Using port {args.port}...")
    
    # Run the application
    try:
        subprocess.run(cmd, env=env)
    except KeyboardInterrupt:
        print("\nApplication stopped by user.")
    finally:
        # Clean up temporary file if created
        if "temp_file" in locals() and os.path.exists(temp_file):
            os.remove(temp_file)
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
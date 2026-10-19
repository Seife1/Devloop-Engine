#!/usr/bin/env python3
"""
LearnLoop CLI with universal integration support.
"""

import argparse
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="LearnLoop - AI Learning Companion")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # init command
    init_parser = subparsers.add_parser("init", help="Initialize LearnLoop in project")
    init_parser.add_argument("--repo", default=".", help="Repository path")
    init_parser.add_argument("--integrate", action="store_true", help="Auto-integrate with IDEs")
    
    # integrate command
    integrate_parser = subparsers.add_parser("integrate", help="Integrate with IDEs/terminal")
    integrate_parser.add_argument("--ide", choices=["auto", "vscode", "cursor", "claude", "windsurf", "zed", "all"], 
                                 default="auto", help="IDE to integrate with")
    integrate_parser.add_argument("--force", action="store_true", help="Force overwrite")
    integrate_parser.add_argument("--terminal", action="store_true", help="Setup terminal integration")
    integrate_parser.add_argument("--env", action="store_true", help="Setup environment")
    integrate_parser.add_argument("--all", action="store_true", help="Setup everything")
    
    # Existing commands (stubs)
    subparsers.add_parser("record-commit", help="Record commit metadata")
    subparsers.add_parser("concepts", help="Regenerate concepts.md")
    subparsers.add_parser("review", help="Interactive review session")
    subparsers.add_parser("briefing", help="Session briefing")
    subparsers.add_parser("techscan", help="Scan technologies")
    subparsers.add_parser("backfill", help="Backfill commit history")
    subparsers.add_parser("doctor", help="Diagnostics")
    subparsers.add_parser("dashboard", help="Start dashboard")
    
    args = parser.parse_args()
    
    if args.command == "integrate":
        # Import and run integrator
        try:
            from learnloop.integrator import LearnLoopIntegrator
            integrator = LearnLoopIntegrator()
            integrator.run(sys.argv[2:])
        except ImportError as e:
            print(f"Error: Integrator module not found: {e}")
            print("Try: pip install -e .")
            sys.exit(1)
    
    elif args.command == "init":
        print("Initializing LearnLoop...")
        # Import and run actual init
        try:
            from learnloop.cli.init import init_project
            init_project(args.repo, args.integrate)
        except ImportError:
            # Fallback for now
            print(f"Initializing in {args.repo}")
            if args.integrate:
                print("Auto-integration requested")
                # Run integration
                from learnloop.integrator import LearnLoopIntegrator
                integrator = LearnLoopIntegrator()
                integrator.run(["--all"])
    
    elif args.command is None:
        parser.print_help()
        print("\n💡 Try: learnloop integrate --all  (for universal integration)")
    
    else:
        print(f"Command '{args.command}' would execute here")
        print("(Implementation details depend on actual modules)")

if __name__ == "__main__":
    main()

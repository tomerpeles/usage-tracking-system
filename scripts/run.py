#!/usr/bin/env python3
"""
Utility script to run the usage tracking system in different modes
"""

import argparse
import asyncio
import logging
import subprocess
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_command(cmd: list, env: dict = None) -> int:
    """Run a command and return exit code"""
    try:
        result = subprocess.run(cmd, env=env, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 130
    except Exception as e:
        print(f"Error running command: {e}")
        return 1


def setup_logging(level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def run_api_gateway():
    """Run the API Gateway service"""
    print("Starting API Gateway...")
    setup_logging()
    
    from services.api_gateway.main import app
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False
    )


async def run_event_processor():
    """Run the Event Processor service"""
    print("Starting Event Processor...")
    setup_logging()
    
    from services.event_processor.main import main
    await main()


def run_query_service():
    """Run the Query Service"""
    print("Starting Query Service...")
    setup_logging()
    
    from services.query_service.main import app
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,
        log_level="info",
        reload=False
    )


async def run_aggregation_service():
    """Run the Aggregation Service"""
    print("Starting Aggregation Service...")
    setup_logging()
    
    from services.aggregation_service.main import main
    await main()


def run_migrations():
    """Run database migrations"""
    print("Running database migrations...")
    return run_command(["python", "-m", "alembic", "upgrade", "head"])


def run_tests():
    """Run the test suite"""
    print("Running tests...")
    return run_command([
        "python", "-m", "pytest", 
        "tests/", 
        "-v", 
        "--cov=services", 
        "--cov=shared",
        "--cov-report=term-missing"
    ])


def run_linting():
    """Run code linting"""
    print("Running linting...")
    
    print("Running flake8...")
    flake8_result = run_command(["python", "-m", "flake8", "services/", "shared/"])
    
    print("Running mypy...")
    mypy_result = run_command(["python", "-m", "mypy", "services/", "shared/"])
    
    print("Running black (check only)...")
    black_result = run_command(["python", "-m", "black", "--check", "."])
    
    print("Running isort (check only)...")
    isort_result = run_command(["python", "-m", "isort", "--check-only", "."])
    
    return max(flake8_result, mypy_result, black_result, isort_result)


def format_code():
    """Format code with black and isort"""
    print("Formatting code...")
    
    print("Running black...")
    black_result = run_command(["python", "-m", "black", "."])
    
    print("Running isort...")
    isort_result = run_command(["python", "-m", "isort", "."])
    
    return max(black_result, isort_result)


def run_docker_build():
    """Build all Docker images"""
    print("Building Docker images...")
    
    services = [
        "api_gateway",
        "event_processor", 
        "query_service",
        "aggregation_service"
    ]
    
    for service in services:
        print(f"Building {service}...")
        result = run_command([
            "docker", "build",
            "-f", f"Dockerfile.{service}",
            "-t", f"usage-tracking-{service}:latest",
            "."
        ])
        if result != 0:
            return result
    
    return 0


def run_docker_up(profile: str = None):
    """Start services with Docker Compose"""
    print("Starting services with Docker Compose...")
    
    cmd = ["docker-compose", "up", "-d"]
    
    if profile:
        cmd.extend(["--profile", profile])
    
    return run_command(cmd)


def run_docker_down():
    """Stop services with Docker Compose"""
    print("Stopping Docker Compose services...")
    return run_command(["docker-compose", "down"])


def run_sdk_example():
    """Run SDK examples"""
    print("Running SDK examples...")
    return run_command(["python", "client_sdk/examples.py"])


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Usage Tracking System Runner")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Service commands
    subparsers.add_parser("api-gateway", help="Run API Gateway service")
    subparsers.add_parser("event-processor", help="Run Event Processor service") 
    subparsers.add_parser("query-service", help="Run Query Service")
    subparsers.add_parser("aggregation-service", help="Run Aggregation Service")
    
    # Database commands
    subparsers.add_parser("migrate", help="Run database migrations")
    
    # Development commands
    subparsers.add_parser("test", help="Run tests")
    subparsers.add_parser("lint", help="Run linting")
    subparsers.add_parser("format", help="Format code")
    
    # Docker commands
    subparsers.add_parser("docker-build", help="Build Docker images")
    docker_up_parser = subparsers.add_parser("docker-up", help="Start with Docker Compose")
    docker_up_parser.add_argument("--profile", help="Docker Compose profile")
    subparsers.add_parser("docker-down", help="Stop Docker Compose")
    
    # SDK commands
    subparsers.add_parser("sdk-example", help="Run SDK examples")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Handle async commands
    async_commands = {
        "event-processor": run_event_processor,
        "aggregation-service": run_aggregation_service,
    }
    
    if args.command in async_commands:
        try:
            asyncio.run(async_commands[args.command]())
            return 0
        except KeyboardInterrupt:
            print("\nService stopped by user")
            return 0
        except Exception as e:
            print(f"Error: {e}")
            return 1
    
    # Handle sync commands
    sync_commands = {
        "api-gateway": run_api_gateway,
        "query-service": run_query_service,
        "migrate": run_migrations,
        "test": run_tests,
        "lint": run_linting,
        "format": format_code,
        "docker-build": run_docker_build,
        "docker-down": run_docker_down,
        "sdk-example": run_sdk_example,
    }
    
    if args.command in sync_commands:
        return sync_commands[args.command]()
    
    if args.command == "docker-up":
        return run_docker_up(args.profile)
    
    print(f"Unknown command: {args.command}")
    return 1


if __name__ == "__main__":
    exit(main())
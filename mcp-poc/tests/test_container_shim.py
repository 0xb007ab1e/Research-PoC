#!/usr/bin/env python3
"""
Unit tests for the container shim script
"""
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch, MagicMock

SCRIPT_DIR = os.path.dirname(os.path.dirname(__file__))


class TestContainerShim(unittest.TestCase):
    def setUp(self):
        self.script_path = os.path.join(SCRIPT_DIR, "scripts", "container.sh")
        
    def test_script_exists_and_executable(self):
        """Test that the container.sh script exists and is executable"""
        self.assertTrue(os.path.exists(self.script_path))
        self.assertTrue(os.access(self.script_path, os.X_OK))
    
    def test_invalid_command(self):
        """Test handling of invalid commands"""
        result = subprocess.run([
            self.script_path, 'invalid_command'
        ], capture_output=True, text=True)
        
        self.assertIn("Unknown command: invalid_command", result.stdout + result.stderr)
        self.assertNotEqual(result.returncode, 0)
    
    def test_no_arguments(self):
        """Test behavior when no arguments are provided"""
        result = subprocess.run([
            self.script_path
        ], capture_output=True, text=True)
        
        self.assertIn("Unknown command:", result.stdout + result.stderr)
        self.assertNotEqual(result.returncode, 0)
    
    def test_environment_variables_exported(self):
        """Test that CONTAINER_CMD and COMPOSE_CMD are properly set"""
        # Create a test script that prints the environment variables
        test_script = """#!/bin/bash
set -e
# Source the container script without executing it
source {}
echo "CONTAINER_CMD=${{CONTAINER_CMD}}"
echo "COMPOSE_CMD=${{COMPOSE_CMD}}"
""".format(self.script_path)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False, dir=SCRIPT_DIR) as f:
            f.write(test_script)
            temp_script = f.name
        
        try:
            os.chmod(temp_script, 0o755)
            result = subprocess.run([temp_script], shell=True, executable='/bin/bash', capture_output=True, text=True)
            
            # Should contain either docker or podman
            output = result.stdout
            if result.returncode == 0:
                self.assertTrue(
                    "CONTAINER_CMD=docker" in output or "CONTAINER_CMD=podman" in output,
                    f"Expected CONTAINER_CMD to be set, got: {output}"
                )
                self.assertTrue(
                    "COMPOSE_CMD=" in output,
                    f"Expected COMPOSE_CMD to be set, got: {output}"
                )
            else:
                # If no container engine is installed, that's okay for this test
                self.assertIn("No container engine found", result.stderr)
        finally:
            os.unlink(temp_script)


class TestContainerShimMocked(unittest.TestCase):
    """Test with mocked environments to ensure proper behavior"""
    
    def setUp(self):
        with open(os.path.join(SCRIPT_DIR, "scripts", "container.sh")) as f:
            self.script_content = f.read()
    
    def test_docker_priority_over_podman(self):
        """Test that Docker takes priority over Podman when both are available"""
        # This would require more complex mocking, but the logic is clear in the script
        # Docker is checked first, so it will be chosen if available
        script_lines = self.script_content.split('\n')
        docker_check_line = None
        podman_check_line = None
        
        for i, line in enumerate(script_lines):
            if 'command -v docker' in line:
                docker_check_line = i
            elif 'command -v podman' in line:
                podman_check_line = i
        
        self.assertIsNotNone(docker_check_line, "Docker check not found")
        self.assertIsNotNone(podman_check_line, "Podman check not found")
        self.assertLess(docker_check_line, podman_check_line, "Docker should be checked before Podman")
    
    def test_compose_command_logic(self):
        """Test that compose command handling is correct"""
        # Verify the script contains proper compose handling
        self.assertIn('compose)', self.script_content)
        self.assertIn('shift', self.script_content)
        self.assertIn('exec $COMPOSE_CMD', self.script_content)
    
    def test_supported_commands(self):
        """Test that all required commands are supported"""
        required_commands = ['build', 'run', 'login', 'push', 'compose']
        
        for command in required_commands:
            if command == 'compose':
                self.assertIn(f'{command})', self.script_content)
            else:
                self.assertIn(command, self.script_content)


if __name__ == '__main__':
    unittest.main()

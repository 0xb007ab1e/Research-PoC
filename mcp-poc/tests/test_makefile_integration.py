#!/usr/bin/env python3
"""
Test script for Makefile integration with container-env.mk
"""
import os
import subprocess
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.dirname(__file__))


class TestMakefileIntegration(unittest.TestCase):
    def setUp(self):
        self.makefile_include = os.path.join(SCRIPT_DIR, "scripts", "container-env.mk")
        
    def test_makefile_include_exists(self):
        """Test that the Makefile include exists"""
        self.assertTrue(os.path.exists(self.makefile_include))
    
    def test_container_info_target(self):
        """Test that the container-info target works"""
        result = subprocess.run([
            'make', '-f', self.makefile_include, 'container-info'
        ], capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("Container engine:", result.stdout)
        self.assertIn("Compose command:", result.stdout)
    
    def test_makefile_variables_exported(self):
        """Test that variables are properly exported in Makefiles"""
        # Create a test Makefile that includes our container-env.mk
        test_makefile = """
include {include_path}

.PHONY: test-vars
test-vars:
\t@echo "CONTAINER_CMD=$(CONTAINER_CMD)"
\t@echo "COMPOSE_CMD=$(COMPOSE_CMD)"
""".format(include_path=self.makefile_include)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mk', delete=False) as f:
            f.write(test_makefile)
            temp_makefile = f.name
        
        try:
            result = subprocess.run([
                'make', '-f', temp_makefile, 'test-vars'
            ], capture_output=True, text=True)
            
            self.assertEqual(result.returncode, 0)
            output = result.stdout
            self.assertTrue(
                "CONTAINER_CMD=docker" in output or "CONTAINER_CMD=podman" in output,
                f"Expected CONTAINER_CMD to be set, got: {output}"
            )
            self.assertIn("COMPOSE_CMD=", output)
        finally:
            os.unlink(temp_makefile)


if __name__ == '__main__':
    unittest.main()

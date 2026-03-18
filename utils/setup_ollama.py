"""
Ollama Setup Utility

Checks if Ollama is installed, running, and has required models.
Pulls models if needed.
"""
import subprocess
import sys
import time
from typing import List, Optional


class OllamaSetup:
    """
    Ollama setup and verification utility
    """
    
    REQUIRED_MODELS = [
        "qwen3.5:0.8b",  # Vision analysis
    ]
    
    def __init__(self):
        self.ollama_host = "http://localhost:11434"
    
    def check_ollama_installed(self) -> bool:
        """
        Check if Ollama is installed on the system
        
        Returns:
            True if installed
        """
        try:
            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print(f"✓ Ollama installed: {result.stdout.strip()}")
                return True
            else:
                print("✗ Ollama not installed")
                return False
                
        except FileNotFoundError:
            print("✗ Ollama command not found")
            return False
        except Exception as e:
            print(f"✗ Error checking Ollama: {e}")
            return False
    
    def check_ollama_running(self) -> bool:
        """
        Check if Ollama server is running
        
        Returns:
            True if running
        """
        try:
            from ollama import Client
            
            client = Client(host=self.ollama_host, timeout=5)
            client.list()
            
            print(f"✓ Ollama server running at {self.ollama_host}")
            return True
            
        except Exception as e:
            print(f"✗ Ollama server not running at {self.ollama_host}")
            return False
    
    def start_ollama_server(self) -> bool:
        """
        Start Ollama server in background
        
        Returns:
            True if started successfully
        """
        print("Starting Ollama server...")
        
        try:
            # Start Ollama serve in background
            process = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
            )
            
            # Wait for server to start
            time.sleep(3)
            
            # Check if it's running
            if self.check_ollama_running():
                print("✓ Ollama server started successfully")
                return True
            else:
                print("✗ Failed to start Ollama server")
                return False
                
        except Exception as e:
            print(f"✗ Error starting Ollama: {e}")
            return False
    
    def list_available_models(self) -> List[str]:
        """
        List models available in Ollama
        
        Returns:
            List of model names
        """
        try:
            from ollama import Client
            
            client = Client(host=self.ollama_host)
            response = client.list()
            
            # Handle different response formats
            if isinstance(response, dict) and 'models' in response:
                model_names = [m['name'] for m in response['models']]
            elif hasattr(response, 'models'):
                model_names = [m.name if hasattr(m, 'name') else m['name'] for m in response.models]
            else:
                model_names = []
            
            print(f"\nAvailable models ({len(model_names)}):")
            for model in model_names:
                print(f"  - {model}")
            
            return model_names
            
        except Exception as e:
            print(f"✗ Error listing models: {e}")
            return []
    
    def check_model_available(self, model_name: str) -> bool:
        """
        Check if specific model is available
        
        Args:
            model_name: Model name to check
            
        Returns:
            True if available
        """
        try:
            from ollama import Client
            
            client = Client(host=self.ollama_host)
            response = client.list()
            
            # Handle different response formats
            if isinstance(response, dict) and 'models' in response:
                model_names = [m['name'] for m in response['models']]
            elif hasattr(response, 'models'):
                model_names = [m.name if hasattr(m, 'name') else m['name'] for m in response.models]
            else:
                model_names = []
            
            # Exact match
            if model_name in model_names:
                return True
            
            # Partial match
            for name in model_names:
                if model_name.split(':')[0] in name:
                    print(f"  Found similar model: {name}")
                    return True
            
            return False
            
        except Exception as e:
            print(f"✗ Error checking model: {e}")
            return False
    
    def pull_model(self, model_name: str) -> bool:
        """
        Pull model from Ollama registry
        
        Args:
            model_name: Model to pull
            
        Returns:
            True if pulled successfully
        """
        print(f"\nPulling model: {model_name}")
        print("This may take several minutes depending on your internet connection...")
        print("Downloading...")
        
        try:
            from ollama import Client
            
            client = Client(host=self.ollama_host)
            
            # Pull with progress
            for progress in client.pull(model_name, stream=True):
                if 'completed' in progress and 'total' in progress:
                    completed_mb = progress['completed'] / (1024*1024)
                    total_mb = progress['total'] / (1024*1024)
                    percent = (progress['completed'] / progress['total']) * 100
                    print(f"  Progress: {completed_mb:.1f}/{total_mb:.1f} MB ({percent:.1f}%)", end='\r')
                elif 'status' in progress:
                    print(f"  {progress['status']}", end='\r')
            
            print(f"\n✓ Model {model_name} pulled successfully")
            return True
            
        except Exception as e:
            print(f"\n✗ Error pulling model: {e}")
            return False
    
    def setup_required_models(self, auto_pull: bool = True) -> bool:
        """
        Ensure all required models are available
        
        Args:
            auto_pull: Automatically pull missing models
            
        Returns:
            True if all models available
        """
        print("\n" + "="*60)
        print("Checking Required Models")
        print("="*60)
        
        all_available = True
        
        for model in self.REQUIRED_MODELS:
            print(f"\nChecking: {model}")
            
            if self.check_model_available(model):
                print(f"  ✓ Available")
            else:
                print(f"  ✗ Not found")
                
                if auto_pull:
                    print(f"  → Auto-pulling {model}...")
                    if not self.pull_model(model):
                        all_available = False
                else:
                    # Ask to pull
                    response = input(f"  Pull {model}? (y/n): ").strip().lower()
                    if response == 'y':
                        if not self.pull_model(model):
                            all_available = False
                    else:
                        print(f"  ⊘ Skipped pulling {model}")
                        all_available = False
        
        return all_available
    
    def run_full_setup(self) -> bool:
        """
        Run complete Ollama setup
        
        Returns:
            True if setup successful
        """
        print("\n" + "="*60)
        print("Ollama Setup Utility")
        print("="*60)
        
        # Step 1: Check installation
        print("\n[1/4] Checking Ollama installation...")
        if not self.check_ollama_installed():
            print("\n✗ Ollama is not installed.")
            print("\nInstall Ollama:")
            print("  Windows: https://ollama.ai/download/OllamaSetup.exe")
            print("  macOS:   brew install ollama")
            print("  Linux:   curl -fsSL https://ollama.ai/install.sh | sh")
            return False
        
        # Step 2: Check server running
        print("\n[2/4] Checking Ollama server...")
        if not self.check_ollama_running():
            print("\nAttempting to start Ollama server...")
            if not self.start_ollama_server():
                print("\n✗ Please start Ollama manually:")
                print("  ollama serve")
                return False
        
        # Step 3: List available models
        print("\n[3/4] Listing available models...")
        available_models = self.list_available_models()
        
        # Step 4: Check required models
        print("\n[4/4] Checking required models...")
        if self.setup_required_models():
            print("\n" + "="*60)
            print("✓ Ollama Setup Complete!")
            print("="*60)
            return True
        else:
            print("\n" + "="*60)
            print("⚠ Setup Incomplete - Some models missing")
            print("="*60)
            print("\nYou can pull missing models later with:")
            print("  ollama pull qwen3.5:0.8b")
            return False


def main():
    """Main entry point"""
    setup = OllamaSetup()
    success = setup.run_full_setup()
    
    if success:
        print("\n✓ Everything is ready! You can now run the vision agent tests.")
        print("\nTest command:")
        print("  pytest tests/agents/test_vision_agent.py -v")
    else:
        print("\n⚠ Setup incomplete. Please install missing components.")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

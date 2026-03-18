"""
Ollama Model Manager

Lists, deletes, and pulls Ollama models.
"""
import sys
from ollama import Client


class OllamaModelManager:
    """Manage Ollama models"""
    
    def __init__(self, host="http://localhost:11434"):
        self.client = Client(host=host)
        self.host = host
    
    def list_models(self):
        """List all available models"""
        print("\n" + "="*60)
        print(f"Ollama Models at {self.host}")
        print("="*60)
        
        try:
            response = self.client.list()
            
            if isinstance(response, dict) and 'models' in response:
                models = response['models']
            elif hasattr(response, 'models'):
                models = response.models
            else:
                print("No models found")
                return []
            
            if not models:
                print("No models available")
                return []
            
            print(f"\nFound {len(models)} model(s):\n")
            
            for i, model in enumerate(models, 1):
                if isinstance(model, dict):
                    name = model.get('name', 'unknown')
                    size = model.get('size', 0)
                    modified = model.get('modified_at', 'unknown')
                else:
                    name = getattr(model, 'name', 'unknown')
                    size = getattr(model, 'size', 0)
                    modified = getattr(model, 'modified_at', 'unknown')
                
                size_gb = size / (1024**3) if size else 0
                print(f"  {i}. {name}")
                print(f"     Size: {size_gb:.2f} GB")
                print(f"     Modified: {modified}")
                print()
            
            return [m['name'] if isinstance(m, dict) else m.name for m in models]
            
        except Exception as e:
            print(f"Error listing models: {e}")
            return []
    
    def delete_model(self, model_name: str) -> bool:
        """
        Delete a model
        
        Args:
            model_name: Name of model to delete
            
        Returns:
            True if deleted successfully
        """
        print(f"\nDeleting model: {model_name}...")
        
        try:
            self.client.delete(model_name)
            print(f"✓ Model '{model_name}' deleted successfully")
            return True
        except Exception as e:
            print(f"✗ Failed to delete '{model_name}': {e}")
            return False
    
    def pull_model(self, model_name: str) -> bool:
        """
        Pull a model from Ollama registry
        
        Args:
            model_name: Name of model to pull
            
        Returns:
            True if pulled successfully
        """
        print(f"\nPulling model: {model_name}")
        print("This may take several minutes...")
        
        try:
            print("Downloading...\n")
            
            for progress in self.client.pull(model_name, stream=True):
                if 'completed' in progress and 'total' in progress:
                    completed_mb = progress['completed'] / (1024*1024)
                    total_mb = progress['total'] / (1024*1024)
                    percent = (progress['completed'] / progress['total']) * 100
                    print(f"  Progress: {completed_mb:.1f}/{total_mb:.1f} MB ({percent:.1f}%)", end='\r')
                elif 'status' in progress:
                    print(f"  {progress['status']}", end='\r')
            
            print(f"\n\n✓ Model '{model_name}' pulled successfully")
            return True
            
        except Exception as e:
            print(f"\n✗ Failed to pull '{model_name}': {e}")
            return False
    
    def delete_and_pull(self, delete_models: list, pull_models: list):
        """
        Delete specified models and pull new ones
        
        Args:
            delete_models: List of model names to delete
            pull_models: List of model names to pull
        """
        print("\n" + "="*60)
        print("Ollama Model Manager")
        print("="*60)
        
        # List current models
        current_models = self.list_models()
        
        # Delete specified models
        if delete_models:
            print("\n" + "="*60)
            print("Deleting Models")
            print("="*60)
            
            for model_name in delete_models:
                # Check if model exists
                if any(model_name in m for m in current_models):
                    self.delete_model(model_name)
                else:
                    print(f"\n⊘ Model '{model_name}' not found - skipping")
        
        # Pull new models
        if pull_models:
            print("\n" + "="*60)
            print("Pulling Models")
            print("="*60)
            
            for model_name in pull_models:
                self.pull_model(model_name)
        
        # Show final list
        print("\n" + "="*60)
        print("Final Model List")
        print("="*60)
        self.list_models()


def main():
    """Main entry point"""
    manager = OllamaModelManager()
    
    # Models to delete and pull
    DELETE_MODELS = ["phi"]  # Delete phi model
    PULL_MODELS = ["qwen3.5:0.8b"]  # Pull Qwen for vision
    
    print("\nThis script will:")
    print(f"  1. Delete: {', '.join(DELETE_MODELS) if DELETE_MODELS else 'None'}")
    print(f"  2. Pull: {', '.join(PULL_MODELS) if PULL_MODELS else 'None'}")
    print()
    
    response = input("Continue? (y/n): ").strip().lower()
    
    if response != 'y':
        print("Aborted")
        sys.exit(0)
    
    manager.delete_and_pull(DELETE_MODELS, PULL_MODELS)
    
    print("\n" + "="*60)
    print("✓ Model Management Complete!")
    print("="*60)
    print("\nYou can now run vision agent tests:")
    print("  pytest tests/agents/test_vision_agent.py -v")


if __name__ == "__main__":
    main()

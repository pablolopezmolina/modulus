import os

def print_directory_tree(startpath):
    print(f"\n📂 ESTRUCTURA ACTUAL DE: {os.path.abspath(startpath)}\n")
    
    for root, dirs, files in os.walk(startpath):
        # Filtramos carpetas que no nos interesan para no ensuciar el output
        dirs[:] = [d for d in dirs if d not in ['.git', '.idea', '__pycache__', 'venv', 'env', '.pytest_cache', '.vscode']]
        
        level = root.replace(startpath, '').count(os.sep)
        indent = '│   ' * (level)
        print(f'{indent}├── {os.path.basename(root)}/')
        
        subindent = '│   ' * (level + 1)
        for f in files:
            # Ignoramos archivos de sistema o compilados
            if not f.startswith('.') and not f.endswith('.pyc'):
                print(f'{subindent}├── {f}')

if __name__ == "__main__":
    print_directory_tree('.')
import os

backend_dir = 'backend'
for root, _, files in os.walk(backend_dir):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = content.replace('from backend.', 'from ')
            new_content = new_content.replace('import backend.', 'import ')
            
            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Fixed imports in {filepath}")

# Ensure __init__.py files exist
dirs = ['backend', 'backend/api', 'backend/services', 'backend/core', 'backend/models', 'backend/storage']
for d in dirs:
    init_path = os.path.join(d, '__init__.py')
    if not os.path.exists(init_path):
        with open(init_path, 'w', encoding='utf-8') as f:
            f.write('')
        print(f"Created {init_path}")

print("Done with Priority 1 fixes.")

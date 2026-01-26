import os
import sys
from pathlib import Path
import django
from django.db import connection

# Set up the environment
# Assuming this script is in backend/scripts/
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent
sys.path.append(str(backend_dir))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    django.setup()
    print("Django setup successful.")
except Exception as e:
    print(f"Error setting up Django: {e}")
    sys.exit(1)

def clear_migrations():
    """
    Deletes all migration files inside apps/*/migrations/
    except for __init__.py directories.
    """
    apps_dir = backend_dir / 'apps'
    if not apps_dir.exists():
        print(f"Apps directory not found at {apps_dir}")
        return

    print("Scanning for migration files...")
    
    deleted_count = 0
    # Walk through the apps directory
    for root, dirs, files in os.walk(apps_dir):
        if 'migrations' in dirs:
            migrations_dir = Path(root) / 'migrations'
            
            # Iterate over files in the migrations directory
            for file in migrations_dir.iterdir():
                if file.is_file() and file.name != '__init__.py' and file.name != '__pycache__':
                    try:
                        file.unlink()
                        print(f"Deleted: {file}")
                        deleted_count += 1
                    except Exception as e:
                        print(f"Failed to delete {file}: {e}")
            
            # Ensure __init__.py exists
            init_file = migrations_dir / '__init__.py'
            if not init_file.exists():
                init_file.touch()
                print(f"Created missing __init__.py in {migrations_dir}")

    print(f"Finished. Deleted {deleted_count} migration files.")

def reset_database():
    """
    Resets the Postgres database by dropping and recreating the public schema.
    This effectively deletes all tables and data.
    """
    print("Resetting database (dropping public schema)...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("DROP SCHEMA public CASCADE;")
            cursor.execute("CREATE SCHEMA public;")
            # Grant usage on schema public to public; (optional, but standard)
            # cursor.execute("GRANT ALL ON SCHEMA public TO public;") 
            # Note: The above line might fail if the user is not superuser, 
            # but usually the owner works fine. The default permissions are usually enough.
            # However, 'CREATE SCHEMA public' resets it to default owner.
            
        print("Successfully reset database schema.")
    except Exception as e:
        print(f"Error checking database: {e}")
        print("Ensure your database is running and configured correctly in settings.py.")
        print("Note: This script assumes you are using PostgreSQL.")

if __name__ == "__main__":
    print("WARNING: This script will:")
    print("1. Delete all migration files (excluding __init__.py)")
    print("2. DROP the entire 'public' schema in your database (ALL DATA WILL BE LOST)")
    print("Make sure your Postgres database is running.")
    choice = input("Are you sure you want to proceed? (yes/no): ")
    
    if choice.lower() == 'yes':
        clear_migrations()
        reset_database()
        print("\nProcess completed.")
        print("Next steps:")
        print("1. python manage.py makemigrations")
        print("2. python manage.py migrate")
    else:
        print("Operation cancelled.")

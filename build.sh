set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

python manage.py migrate

echo "Creating distributor user..."
cat <<EOF | python manage.py shell
from users.models import User

username = "admin"
password = "admin123"
email = "admin@example.com"

if not User.objects.filter(username=username).exists():
    print(f"Creating distributor user: {username}")
    User.objects.create_superuser(
        username=username,
        password=password,
        email=email,
        role='DISTRIBUTOR'
    )
    print("Distributor user created successfully.")
else:
    print(f"Distributor user {username} already exists.")
EOF
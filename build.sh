set -o errexit

pip install -r requirements.txt

python3 manage.py collectstatic --no-input

python3 manage.py migrate

echo "Creating or updating distributor user..."
cat <<EOF | python3 manage.py shell
from users.models import User

username = "admin2"
password = "admin123"

user, created = User.objects.get_or_create(username=username)

if created:
    print(f"Creating new distributor user: {username}")
    user.set_password(password)
else:
    print(f"User {username} already exists. Ensuring role is correct.")

user.is_staff = True
user.is_superuser = True
user.role = 'DISTRIBUTOR'
user.save()

print(f"User {username} successfully configured as a distributor.")
EOF
# Management Commands for Restaurant-365

## onboard_restaurant

**Usage:**

    python manage.py onboard_restaurant "<restaurant_name>"

Creates a new restaurant with the provided name (or gets it if it already exists) and prints the restaurant's ID.

---

## add_staff

**Usage:**

    python manage.py add_staff <restaurant_id> <username> <role>
    python manage.py add_staff <username> <role> --password <password> <restaurant_id>

Creates a Django user with the given username and a password (randomly generated if not provided, or set to the value of --password), and creates a staff entry for the specified restaurant and role (waiter, manager, owner). Prints the username, password, staff role, and restaurant name. If the user already exists as staff for another restaurant, the command aborts and prints an error.

---

These commands help automate onboarding of restaurants and staff for your Restaurant-365 deployment.

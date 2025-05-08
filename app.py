import os
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session # Added flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user # Added Flask-Login
from pymongo import MongoClient, ASCENDING, DESCENDING, UpdateOne 
from datetime import datetime, timedelta, timezone
from bson import ObjectId, BSON 
import json
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash # Added hashing
from functools import wraps

# Load environment variables
load_dotenv()

app = Flask(__name__)

# --- Configuration ---
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY", "default_secret_key_change_me") # Essential for sessions
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    print("CRITICAL ERROR: MONGO_URI environment variable not set.")
DB_NAME = "cs2_tracker_db"
VALID_INVITE_CODES = set(os.getenv("VALID_INVITE_CODES", "").split(',')) # Load invite codes

# --- Database Connection ---
try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    accounts_collection = db.accounts
    cases_collection = db.cases # Will now have 'case_price'
    progress_collection = db.weekly_progress
    users_collection = db.users # Will now have 'user_type'
    client.admin.command('ping')
    print("Successfully connected to MongoDB!")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
    exit()

# --- Flask-Login Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Redirect to login page if @login_required fails
login_manager.login_message_category = 'info' # Bootstrap class for flash message

# --- User Model (ADD user_type) ---
class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.password_hash = user_data['password_hash']
        self.user_type = user_data.get('user_type', 'user') # Default to 'user'
        self._mongo_id = user_data['_id']

    def is_admin(self):
        return self.user_type == 'Admin'

    # ... (keep check_password, get_id_obj, get, find_by_username) ...
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id_obj(self):
        return self._mongo_id

    @staticmethod
    def get(user_id):
        try:
            user_data = users_collection.find_one({'_id': ObjectId(user_id)})
            if user_data:
                return User(user_data)
        except Exception: # Be more specific with exceptions if possible
            pass
        return None

    @staticmethod
    def find_by_username(username):
        return users_collection.find_one({'username': username})


@login_manager.user_loader
def load_user(user_id):
    """Flask-Login callback to load a user from the session."""
    return User.get(user_id)

# --- Admin Required Decorator ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


# --- Helper Functions ---
def get_most_recent_wednesday(today=None):
    """Calculates the date of the most recent Wednesday (or today if it's Wednesday)."""
    if today is None:
        today = datetime.now(timezone.utc).date() # Use timezone-aware datetime
    days_since_wednesday = (today.weekday() - 2 + 7) % 7
    most_recent_wednesday = today - timedelta(days=days_since_wednesday)
    return datetime.combine(most_recent_wednesday, datetime.min.time(), tzinfo=timezone.utc)

def get_previous_week_start(current_wednesday):
    """Calculates the Wednesday of the week before the given Wednesday."""
    return current_wednesday - timedelta(weeks=1)

# No longer needed directly in JSON responses if we avoid sending ObjectIds
# def object_id_str(obj): ...

# --- Authentication Routes ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        invite_code = request.form.get('invite_code')

        # Validation
        if not all([username, password, confirm_password, invite_code]):
            flash('All fields are required.', 'warning')
            return redirect(url_for('register'))
        if password != confirm_password:
            flash('Passwords do not match.', 'warning')
            return redirect(url_for('register'))
        if invite_code not in VALID_INVITE_CODES:
            flash('Invalid invite code.', 'danger')
            return redirect(url_for('register'))
        if User.find_by_username(username):
            flash('Username already exists.', 'warning')
            return redirect(url_for('register'))

        # Create user
        hashed_password = generate_password_hash(password)
        try:
            users_collection.insert_one({
                'username': username,
                'password_hash': hashed_password,
                'registered_at': datetime.now(timezone.utc),
                'used_invite_code': invite_code, # Store which code was used
                'user_type': 'user' # Explicitly set new users to 'user'
            })
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Registration failed: {e}', 'danger')
            print(f"Error registering user {username}: {e}")
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True # Optional: add a checkbox in the form later

        user_data = User.find_by_username(username)

        if not user_data:
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('login'))

        user = User(user_data) # Create User object

        if not user.check_password(password):
             flash('Invalid username or password.', 'danger')
             return redirect(url_for('login'))

        # Log user in
        login_user(user, remember=remember)
        flash(f'Welcome back, {user.username}!', 'success')

        # Redirect to intended page or index
        next_page = request.args.get('next')
        return redirect(next_page or url_for('index'))

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


# --- Account Management Routes (User Specific) ---
@app.route('/manage_accounts')
@login_required
def manage_accounts():
    # Fetch accounts SORTED BY the display order
    user_accounts = list(accounts_collection.find(
        {'user_id': current_user.get_id_obj()}
    ).sort("sort_number", ASCENDING)) # Ensure sorting here
    return render_template('manage_accounts.html', user_accounts=user_accounts)

@app.route('/add_tracked_account', methods=['POST'])
@login_required
def add_tracked_account():
    account_name = request.form.get('account_name')
    steamid_str = request.form.get('steamid')
    # sort_number is no longer taken from the form

    if not account_name or not steamid_str:
        flash("Account Name and SteamID64 are required.", "warning")
        return redirect(url_for('manage_accounts'))

    if not steamid_str.isdigit() or len(steamid_str) != 17:
         flash("Invalid SteamID64 format. Must be 17 digits.", "warning")
         return redirect(url_for('manage_accounts'))

    user_id = current_user.get_id_obj()

    # Check if steamid already exists for this user
    existing = accounts_collection.find_one({
        'user_id': user_id,
        'steamid': steamid_str
    })
    if existing:
        flash(f"Account with SteamID {steamid_str} is already being tracked.", "warning")
        return redirect(url_for('manage_accounts'))

    try:
        # Assign a default high sort number initially, it will be set properly on first save order
        # Or determine the next highest number for this user
        max_sort_doc = accounts_collection.find_one(
            {'user_id': user_id},
            sort=[("sort_number", DESCENDING)]
        )
        next_sort_number = (max_sort_doc['sort_number'] + 1) if max_sort_doc and 'sort_number' in max_sort_doc else 0

        accounts_collection.insert_one({
            'user_id': user_id,
            'account_name': account_name,
            'steamid': steamid_str,
            'sort_number': next_sort_number, # Assign next available sort number
            'added_at': datetime.now(timezone.utc)
        })
        flash(f"Account '{account_name}' added successfully. You may need to drag it to the desired position and save the order.", "success")
    except Exception as e:
        flash(f"Error adding account: {e}", "danger")
        print(f"Error adding account for user {user_id}: {e}")

    return redirect(url_for('manage_accounts'))

@app.route('/update_account_order', methods=['POST'])
@login_required
def update_account_order():
    """Receives a list of account IDs in the desired order and updates sort_number."""
    data = request.get_json()
    if not data or 'ordered_ids' not in data or not isinstance(data['ordered_ids'], list):
        return jsonify({"success": False, "error": "Invalid data format received."}), 400

    ordered_ids_str = data['ordered_ids']
    user_id = current_user.get_id_obj()

    try:
        bulk_operations = []
        for index, account_id_str in enumerate(ordered_ids_str):
            try:
                account_obj_id = ObjectId(account_id_str)
            except Exception:
                # Log this error, but potentially continue? Or fail the whole batch?
                # Failing whole batch is safer if order integrity is critical.
                print(f"Invalid ObjectId format '{account_id_str}' received for user {user_id}")
                return jsonify({"success": False, "error": f"Invalid account ID format: {account_id_str}"}), 400

            # Prepare an UpdateOne operation
            # CRITICAL: Filter by user_id to ensure user can only update their own accounts
            bulk_operations.append(
                UpdateOne(
                    {"_id": account_obj_id, "user_id": user_id}, # Security Check!
                    {"$set": {"sort_number": index}} # Set sort_number to the list index
                )
            )

        if not bulk_operations:
             return jsonify({"success": True, "message": "No accounts to update."}) # Or perhaps an error?

        # Execute all updates in bulk
        result = accounts_collection.bulk_write(bulk_operations, ordered=False) # ordered=False allows other updates if one fails

        # Check result (optional but good practice)
        print(f"Bulk write result for user {user_id}: Matched={result.matched_count}, Modified={result.modified_count}")

        if result.matched_count != len(ordered_ids_str):
             # This could mean some IDs didn't exist or didn't belong to the user
             print(f"Warning: Matched count ({result.matched_count}) doesn't equal submitted ID count ({len(ordered_ids_str)}) for user {user_id}")
             # Decide if this is an error state or just informational
             # Returning success might be okay if non-matching IDs were invalid anyway

        return jsonify({"success": True, "message": "Order updated successfully."})

    except Exception as e:
        print(f"Error updating account order for user {user_id}: {e}")
        return jsonify({"success": False, "error": "An internal server error occurred."}), 500


@app.route('/delete_tracked_account/<account_id>', methods=['POST'])
@login_required
def delete_tracked_account(account_id):
    # ... (Keep existing delete logic - it doesn't need sort_number) ...
    # Consider if you need to re-calculate sort_numbers for remaining accounts after deletion.
    # For simplicity, we won't do that here, gaps in sort_number are okay as long as fetching sorts correctly.
    try:
        obj_id = ObjectId(account_id)
        # IMPORTANT: Ensure the account belongs to the current user before deleting
        result = accounts_collection.delete_one({
            '_id': obj_id,
            'user_id': current_user.get_id_obj() # Security check
        })
        if result.deleted_count == 1:
            flash("Account deleted successfully.", "success")
            # Optional: Add logic here to re-sequence sort_number for remaining accounts if desired
        else:
            flash("Account not found or you do not have permission to delete it.", "danger")
    except Exception as e:
        flash(f"Error deleting account: {e}", "danger")
        print(f"Error deleting account {account_id} for user {current_user.id}: {e}")

    return redirect(url_for('manage_accounts'))


# --- ADMIN ROUTES ---
@app.route('/admin/cases', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_manage_cases():
    if request.method == 'POST':
        try:
            for case_id_str, price_str in request.form.items():
                if not case_id_str.startswith("price_"): # Ensure we are processing price fields
                    continue
                actual_case_id_str = case_id_str.replace("price_", "")

                if not price_str: # If price is empty, maybe set to 0 or skip
                    price = 0.0
                else:
                    try:
                        price = float(price_str)
                        if price < 0: price = 0.0 # Price cannot be negative
                    except ValueError:
                        flash(f"Invalid price format for case ID {actual_case_id_str}.", "warning")
                        continue # Skip this update

                cases_collection.update_one(
                    {"_id": ObjectId(actual_case_id_str)},
                    {"$set": {"case_price": price}}
                )
            flash("Case prices updated successfully.", "success")
        except Exception as e:
            flash(f"Error updating case prices: {e}", "danger")
            print(f"Error updating case prices: {e}")
        return redirect(url_for('admin_manage_cases'))

    all_cases = list(cases_collection.find().sort("case_name", ASCENDING))
    return render_template('admin_cases.html', cases=all_cases)



# --- Core Application Routes (MODIFIED for price display) ---
@app.route('/')
@login_required
def index():
    try:
        user_id = current_user.get_id_obj()
        user_accounts = list(accounts_collection.find(
            {'user_id': user_id}
        ).sort("sort_number", ASCENDING))

        # Fetch all cases with their prices into a dictionary for quick lookup
        all_cases_list = list(cases_collection.find({}, {"case_name": 1, "case_price": 1, "release_date": 1}))
        case_price_map = {case['case_name']: case.get('case_price', 0.0) for case in all_cases_list}
        
        # For dropdowns (sorted by release date)
        cases_for_dropdown = sorted(all_cases_list, key=lambda x: x.get('release_date', datetime.min.replace(tzinfo=timezone.utc)), reverse=True)


        current_wednesday = get_most_recent_wednesday()
        last_wednesday = get_previous_week_start(current_wednesday)

        def get_progress_for_week(week_start_date, user_accounts_list, local_case_price_map):
            account_doc_id_map = {acc['_id']: acc for acc in user_accounts_list}
            account_ids_tracked = [acc['_id'] for acc in user_accounts_list]

            progress_cursor = progress_collection.find({
                "user_id": user_id,
                "week_start": week_start_date,
                "account_doc_id": {"$in": account_ids_tracked}
            })
            progress_list = list(progress_cursor)
            detailed_progress_map = {}
            week_total_price = 0.0

            for entry in progress_list:
                account_info = account_doc_id_map.get(entry.get('account_doc_id'))
                if account_info:
                    case_val = 0.0
                    if entry.get("drop_farmed") and entry.get("case_name"):
                        case_val = local_case_price_map.get(entry["case_name"], 0.0)
                        week_total_price += case_val

                    detailed_entry = {
                        "_id": entry["_id"],
                        "account_name": account_info["account_name"],
                        "steamid": account_info["steamid"],
                        "account_doc_id": account_info["_id"],
                        "week_start": entry["week_start"],
                        "drop_farmed": entry["drop_farmed"],
                        "case_name": entry.get("case_name", ""),
                        "additional_drop": entry.get("additional_drop", ""),
                        "case_value": case_val # Store calculated value
                    }
                    detailed_progress_map[account_info["_id"]] = detailed_entry

            final_detailed_progress = []
            for acc in user_accounts_list:
                if acc['_id'] in detailed_progress_map:
                    final_detailed_progress.append(detailed_progress_map[acc['_id']])
                else:
                    final_detailed_progress.append({
                        "_id": None, "account_name": acc["account_name"], "steamid": acc["steamid"],
                        "account_doc_id": acc["_id"], "week_start": week_start_date,
                        "drop_farmed": False, "case_name": "N/A", "additional_drop": "-",
                        "case_value": 0.0
                    })
            return final_detailed_progress, week_total_price

        current_week_data, current_week_total_value = get_progress_for_week(current_wednesday, user_accounts, case_price_map)
        last_week_data, last_week_total_value = get_progress_for_week(last_wednesday, user_accounts, case_price_map)

        accounts_for_dropdown = [{"_id": str(acc['_id']), "name": acc['account_name']} for acc in user_accounts]
        
        # Use cases_for_dropdown which is already sorted
        cases_for_dropdown_render = [{"name": case['case_name']} for case in cases_for_dropdown]


        return render_template(
            'index.html',
            user_accounts_for_dropdown=accounts_for_dropdown,
            cases=cases_for_dropdown_render, # Pass the sorted list for dropdown
            current_week_start_str=current_wednesday.strftime('%Y-%m-%d'),
            current_week_data=current_week_data,
            current_week_total_value=current_week_total_value,
            last_week_data=last_week_data,
            last_week_total_value=last_week_total_value,
            last_week_start_str=last_wednesday.strftime('%Y-%m-%d')
        )
    except Exception as e:
        print(f"Error in index route for user {current_user.id}: {e}")
        flash(f"An error occurred while loading data: {e}", "danger")
        return render_template('error.html', error_message=str(e)), 500 # Create error.html if it doesn't exist
        

@app.route('/add_progress', methods=['POST'])
@login_required
def add_progress():
    """Adds or updates a weekly progress entry for the current user."""
    try:
        user_id = current_user.get_id_obj()
        account_doc_id_str = request.form.get('account_doc_id')
        week_start_str = request.form.get('week_start')
        drop_farmed_chk = request.form.get('drop_farmed')
        case_name = request.form.get('case_name')
        additional_drop = request.form.get('additional_drop', '')

        # --- Validation/Conversion ---
        if not all([account_doc_id_str, week_start_str]):
             flash("Missing required fields (Account or Week Start)", 'warning')
             return redirect(url_for('index')) # Redirect early on validation fail

        try:
             account_doc_id = ObjectId(account_doc_id_str)
             account_check = accounts_collection.find_one({
                 "_id": account_doc_id,
                 "user_id": user_id
             })
             if not account_check:
                 flash("Invalid or unauthorized account selected.", 'danger')
                 return redirect(url_for('index')) # Redirect early
        except Exception:
             flash("Invalid Account ID format.", 'danger')
             return redirect(url_for('index')) # Redirect early

        try:
            week_start_dt = datetime.strptime(week_start_str, '%Y-%m-%d')
            week_start_utc = datetime.combine(week_start_dt.date(), datetime.min.time(), tzinfo=timezone.utc)
        except ValueError:
            flash("Invalid Date format. Please use YYYY-MM-DD.", 'warning')
            return redirect(url_for('index')) # Redirect early

        drop_farmed = True if drop_farmed_chk == 'on' else False
        case_name_final = case_name if drop_farmed and case_name else None
        additional_drop_final = additional_drop if drop_farmed and additional_drop else None

        # --- Upsert Logic: Update if exists, Insert if not ---
        filter_doc = {
            "user_id": user_id,
            "account_doc_id": account_doc_id,
            "week_start": week_start_utc
        }
        update_doc = {
            "$set": {
                "drop_farmed": drop_farmed,
                "case_name": case_name_final,
                "additional_drop": additional_drop_final,
                "last_updated": datetime.now(timezone.utc)
            },
            "$setOnInsert": {
                 "user_id": user_id,
                 "account_doc_id": account_doc_id,
                 "week_start": week_start_utc
            }
        }

        result = progress_collection.update_one(filter_doc, update_doc, upsert=True)

        if result.upserted_id:
            print(f"Added progress for user {user_id}, account_doc {account_doc_id}, week {week_start_utc}")
            flash("Progress saved successfully.", "success")
        elif result.modified_count > 0:
            print(f"Updated progress for user {user_id}, account_doc {account_doc_id}, week {week_start_utc}")
            flash("Progress updated successfully.", "success")
        else:
             flash("Progress already recorded with this information.", "info")

    except Exception as e:
        print(f"Error adding/updating progress for user {user_id}: {e}")
        flash(f"Failed to save progress: {e}", "danger") # Flash the specific error

    # --- !!! THIS IS THE IMPORTANT LINE TO RESTORE !!! ---
    return redirect(url_for('index'))

@app.route('/update_progress/<progress_id>', methods=['POST'])
@login_required
def update_progress(progress_id):
    """Updates an existing weekly progress entry, ensuring it belongs to the user."""
    try:
        user_id = current_user.get_id_obj()

        # --- Get Data from Form ---
        drop_farmed_chk = request.form.get('edit_drop_farmed')
        case_name = request.form.get('edit_case_name')
        additional_drop = request.form.get('edit_additional_drop', '')

        # --- Data Validation/Conversion ---
        try:
            obj_id = ObjectId(progress_id)
        except Exception:
            flash("Invalid Progress ID format", 'danger')
            return redirect(url_for('index')) # Redirect early

        drop_farmed = True if drop_farmed_chk == 'on' else False
        case_name_final = case_name if drop_farmed and case_name else None
        additional_drop_final = additional_drop if drop_farmed and additional_drop else None

        # --- Create Update Document ---
        update_data = {
            "$set": {
                "drop_farmed": drop_farmed,
                "case_name": case_name_final,
                "additional_drop": additional_drop_final,
                "last_updated": datetime.now(timezone.utc)
            }
        }

        # --- Update in Database (Crucially, check user_id) ---
        result = progress_collection.update_one(
            {"_id": obj_id, "user_id": user_id}, # Ensure this entry belongs to the logged-in user
            update_data
        )

        if result.matched_count == 0:
            flash("Progress entry not found or you don't have permission to edit it.", "warning")
        elif result.modified_count > 0:
             print(f"Updated progress entry {progress_id} for user {user_id}")
             flash("Progress updated successfully.", "success")
        else:
            flash("No changes detected in progress.", "info")

    except Exception as e:
        print(f"Error updating progress {progress_id} for user {user_id}: {e}")
        flash(f"Failed to update progress: {e}", "danger") # Flash the specific error

    # --- !!! THIS IS THE IMPORTANT LINE TO RESTORE !!! ---
    return redirect(url_for('index'))


@app.route('/get_week_data', methods=['GET'])
@login_required
def get_week_data():
    week_start_str = request.args.get('date')
    if not week_start_str:
        return jsonify({"error": "Date parameter is required"}), 400

    try:
        user_id = current_user.get_id_obj()
        week_start_dt = datetime.strptime(week_start_str, '%Y-%m-%d')
        week_start_utc = datetime.combine(week_start_dt.date(), datetime.min.time(), tzinfo=timezone.utc)

        user_accounts = list(accounts_collection.find(
            {"user_id": user_id},
            {"_id": 1, "account_name": 1, "steamid": 1, "sort_number": 1}
        ).sort("sort_number", ASCENDING))

        case_price_map = {case['case_name']: case.get('case_price', 0.0) for case in cases_collection.find({}, {"case_name": 1, "case_price": 1})}

        account_doc_id_map = {acc['_id']: acc for acc in user_accounts}
        account_ids_tracked = list(account_doc_id_map.keys())

        progress_cursor = progress_collection.find({
            "user_id": user_id, "week_start": week_start_utc,
            "account_doc_id": {"$in": account_ids_tracked}
        })
        progress_map = {entry['account_doc_id']: entry for entry in progress_cursor}
        
        detailed_progress = []
        week_total_price = 0.0

        for acc in user_accounts:
            acc_id = acc['_id']
            acc_info = account_doc_id_map.get(acc_id)
            entry = progress_map.get(acc_id)
            
            case_val = 0.0
            if entry and entry.get("drop_farmed") and entry.get("case_name"):
                case_val = case_price_map.get(entry["case_name"], 0.0)
                week_total_price += case_val

            detailed_entry = {
                "account_name": acc_info["account_name"], "steamid": acc_info["steamid"],
                "week_start": week_start_utc.strftime('%Y-%m-%d'),
                "drop_farmed": entry["drop_farmed"] if entry else False,
                "case_name": entry.get("case_name", "") if entry else "N/A",
                "additional_drop": entry.get("additional_drop", "") if entry else "-",
                "progress_id": str(entry["_id"]) if entry else None,
                "case_value": case_val
            }
            detailed_progress.append(detailed_entry)
        
        return jsonify({"progress": detailed_progress, "total_value": week_total_price})

    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400
    except Exception as e:
        print(f"Error fetching week data for '{week_start_str}' for user {current_user.id}: {e}")
        return jsonify({"error": "Failed to fetch data"}), 500

        
@app.route('/edit_tracked_account/<account_id>', methods=['POST'])
@login_required
def edit_tracked_account(account_id):
    """Handles editing an existing tracked account's name and SteamID."""
    user_id = current_user.get_id_obj()

    # --- Get Data from Form ---
    new_account_name = request.form.get('account_name')
    new_steamid = request.form.get('steamid')

    # --- Basic Validation ---
    if not new_account_name or not new_steamid:
        flash("Account Name and SteamID64 are required.", "warning")
        return redirect(url_for('manage_accounts'))

    if not new_steamid.isdigit() or len(new_steamid) != 17:
         flash("Invalid SteamID64 format. Must be 17 digits.", "warning")
         return redirect(url_for('manage_accounts'))

    try:
        account_obj_id = ObjectId(account_id)
    except Exception:
        flash("Invalid Account ID format.", "danger")
        return redirect(url_for('manage_accounts'))

    try:
        # --- Security & Validation ---
        # 1. Find the account AND verify ownership
        original_account = accounts_collection.find_one({
            "_id": account_obj_id,
            "user_id": user_id
        })

        if not original_account:
            # Either ID is wrong OR it doesn't belong to this user
            flash("Account not found or you don't have permission to edit it.", "danger")
            return redirect(url_for('manage_accounts'))

        # 2. Check if the new SteamID is already used by ANOTHER account of THIS user
        if new_steamid != original_account.get('steamid'): # Only check if steamid actually changed
            existing_steamid = accounts_collection.find_one({
                "steamid": new_steamid,
                "user_id": user_id,
                "_id": {"$ne": account_obj_id} # Exclude the current document being edited
            })
            if existing_steamid:
                flash(f"Another account ('{existing_steamid.get('account_name')}') already uses SteamID {new_steamid}.", "warning")
                return redirect(url_for('manage_accounts'))

        # --- Prepare Update ---
        update_data = {
            "account_name": new_account_name,
            "steamid": new_steamid
            # Add 'last_updated': datetime.now(timezone.utc) if desired
        }

        # --- Perform Update ---
        result = accounts_collection.update_one(
            {"_id": account_obj_id, "user_id": user_id}, # Filter remains crucial
            {"$set": update_data}
        )

        if result.matched_count == 0:
             # This case should theoretically be caught by the initial find_one check
             flash("Account not found or you don't have permission to edit it.", "danger")
        elif result.modified_count > 0:
            flash(f"Account '{new_account_name}' updated successfully.", "success")
        else:
            flash("No changes detected for the account.", "info")

    except Exception as e:
        print(f"Error editing account {account_id} for user {user_id}: {e}")
        flash(f"Failed to edit account: {e}", "danger")

    return redirect(url_for('manage_accounts'))

# --- Main Execution ---
if __name__ == '__main__':
    app.run(debug=True, port=5001)
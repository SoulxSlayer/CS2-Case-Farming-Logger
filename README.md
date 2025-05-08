INVITE CODE: CS2CASELOGGERBYSOULXOXO

# CS2 Case Farming Tracker

A Flask and MongoDB web application designed to help CS2 players track their weekly case drops and additional item farming progress across multiple accounts.

## Screenshot:
![{587F642C-9F6D-4392-83D0-4C5FAE5DE029}](https://github.com/user-attachments/assets/08e8d8bb-cadc-4569-a6a8-a4d38a216c46)

## Features

*   **Multi-User System:** Secure registration and login for individual users.
*   **Invite Code Registration:** Control new user sign-ups using invite codes.
*   **Multiple CS2 Account Tracking:** Users can add and manage multiple Steam accounts they wish to track.
*   **Weekly Progress Logging:**
    *   Track if the weekly case drop has been farmed.
    *   Log the name of the case dropped.
    *   Log any additional drops (e.g., graffiti, skins).
*   **Intuitive Interface:**
    *   View progress for the current week and the previous week.
    *   Fetch and view data for any past week.
    *   Drag-and-drop reordering of tracked accounts.
    *   Easy editing of logged progress.
*   **Dark Theme:** User-friendly dark interface.
*   **Steam Profile Links:** Quick links to the inventory of tracked Steam accounts.
*   **Responsive Design:** Built with Bootstrap for usability across devices.

## Tech Stack

*   **Backend:** Python (Flask)
*   **Database:** MongoDB (designed for use with MongoDB Atlas)
*   **Frontend:** HTML, CSS, JavaScript, Bootstrap
*   **Session Management:** Flask-Login
*   **Password Hashing:** Werkzeug
*   **Environment Variables:** python-dotenv
*   **Deployment (Example):** Vercel

## Prerequisites

Before you begin, ensure you have met the following requirements:

*   **Python 3.7+** and `pip` installed.
*   **Git** installed.
*   **MongoDB Atlas Account:** You'll need a MongoDB Atlas cluster.
    *   Get your MongoDB connection string (URI).
    *   Ensure your Atlas cluster's IP Access List allows connections from your local machine (for development) and from `0.0.0.0/0` (for Vercel deployment, or configure Vercel IP ranges if using a paid plan).
*   **A text editor or IDE** (e.g., VS Code).
*   **(Optional for Deployment) Vercel Account:** If you plan to deploy to Vercel.

## Local Development Setup

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd <repository-folder-name>
    ```

2.  **Create and Activate a Virtual Environment:**
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate

    # macOS / Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set Up Environment Variables (.env file):**
    Create a file named `.env` in the root directory of the project. **This file should NOT be committed to Git.** Add the following variables, replacing the placeholder values with your actual credentials and preferences:

    ```dotenv
    MONGO_URI=mongodb+srv://<YOUR_ATLAS_USERNAME>:<YOUR_ATLAS_PASSWORD>@<YOUR_ATLAS_CLUSTER_HOSTNAME>/cs2_tracker_db?retryWrites=true&w=majority
    FLASK_SECRET_KEY='a_very_strong_random_secret_key_for_local_dev'
    VALID_INVITE_CODES='LOCALINVITE1,TESTCODE2'
    ```
    *   **`MONGO_URI`**: Your MongoDB Atlas connection string. Make sure to replace `<YOUR_ATLAS_USERNAME>`, `<YOUR_ATLAS_PASSWORD>`, and `<YOUR_ATLAS_CLUSTER_HOSTNAME>`. The database name (`cs2_tracker_db`) is already in the example.
    *   **`FLASK_SECRET_KEY`**: A long, random string used for session security. Generate one using `python -c "import secrets; print(secrets.token_hex(24))"`.
    *   **`VALID_INVITE_CODES`**: A comma-separated list of invite codes valid for registration on your local instance.

5.  **Ensure MongoDB Indexes (Important for Registration):**
    The `users` collection requires a specific index for the `google_id` field (even if not using Google Sign-In) to prevent registration issues. If you encounter errors about duplicate `google_id: null`, ensure this index is set up correctly in your MongoDB Atlas `cs2_tracker_db.users` collection:
    *   **Field:** `google_id`
    *   **Type:** `1` (Ascending)
    *   **Options:** `Unique: ON`, `Sparse: ON`
    If an older, non-sparse unique index exists on `google_id`, drop it and create this new sparse unique index.

6.  **Run the Flask Application:**
    ```bash
    flask run
    ```
    The application will typically be available at `http://127.0.0.1:5001` (or port 5000 if not specified).

7.  **Access the Application:**
    Open your web browser and go to the address provided by Flask. Register a new user using one of the `VALID_INVITE_CODES` from your `.env` file.

## Using the Application

1.  **Register:** Use a valid invite code to create an account.
2.  **Login:** Log in with your username and password.
3.  **Manage Accounts:**
    *   Navigate to "Manage Accounts".
    *   Add the CS2 accounts you want to track by providing a nickname and their SteamID64.
    *   Drag and drop rows to reorder how accounts appear in tables. Click "Save Order".
    *   Edit or delete tracked accounts.
4.  **Track Progress:**
    *   On the main page, use the "Add / Update Weekly Progress" form to log drops for your accounts.
    *   Select the account, week start date (defaults to current Wednesday), whether the drop was farmed, the case name (if farmed), and any additional drops.
    *   Progress for the current and last week is displayed.
    *   Use the "Other Weeks" section to fetch data for any past Wednesday.
    *   Edit existing progress entries for the current week using the "Edit" button in the table.

## Database Structure (MongoDB Collections)

*   **`users`**: Stores user credentials (username, hashed password, registration info).
*   **`accounts`**: Stores the CS2 accounts tracked by each user (linked via `user_id`, includes account name, SteamID64, display order).
*   **`cases`**: (Global) Stores a list of CS2 case names. You may need to populate this manually or create an interface to manage it.
*   **`weekly_progress`**: Stores the weekly farming progress for each user's tracked accounts (linked via `user_id` and `account_doc_id`).

## Deployment (Example: Vercel)

1.  **Push to a Git Repository:** Ensure your project (excluding `venv/` and `.env`) is on GitHub, GitLab, or Bitbucket.
2.  **`requirements.txt`:** Make sure this file is up-to-date: `pip freeze > requirements.txt`.
3.  **`vercel.json`:** Create this file in your project root:
    ```json
    {
      "version": 2,
      "builds": [
        {
          "src": "app.py",
          "use": "@vercel/python"
        }
      ],
      "routes": [
        {
          "src": "/static/(.*)",
          "dest": "/static/$1"
        },
        {
          "src": "/(.*)",
          "dest": "app.py"
        }
      ]
    }
    ```
4.  **Deploy on Vercel:**
    *   Import your Git repository in Vercel.
    *   **Set Environment Variables in Vercel Project Settings:**
        *   `MONGO_URI`: Your production MongoDB Atlas connection string.
        *   `FLASK_SECRET_KEY`: A **new, strong, random** secret key for production.
        *   `VALID_INVITE_CODES`: Comma-separated invite codes for your live application.
    *   Vercel should detect Flask and deploy.
    *   Ensure your MongoDB Atlas IP Access List allows connections from Vercel (usually `0.0.0.0/0` for free tier Vercel deployments).

## Contributing

Contributions are welcome! Please feel free to fork the repository, make changes, and submit a pull request. For major changes, please open an issue first to discuss what you would like to change.

## License

(Specify your license here, e.g., MIT License)
This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details (if you create one).

---

**Notes for the User of this README:**

*   **Replace Placeholders:** Make sure to replace `<your-repository-url>` and other placeholders.
*   **License File:** If you mention a `LICENSE.md` file, create one (e.g., with the MIT License text).
*   **Cases Collection:** The README mentions the `cases` collection. You might want to add a note about how users can populate this (e.g., "The `cases` collection currently needs to be populated manually in MongoDB Atlas with the names of CS2 cases you want to appear in dropdowns.") or consider adding a simple admin interface for it in the future.
*   **Screenshots:** Consider adding a few screenshots of the application to the README to make it more engaging.
*   **Further Development:** You can add sections like "Future Enhancements" or "Known Issues."


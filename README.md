# EduManager PRO - Student Management System

A production-quality, responsive Student Management System built using Python Flask, MySQL, HTML5, CSS3 (Custom styles), Bootstrap 5, and JavaScript.

This application follows a clean MVC-style architecture. It is fully ready for local testing and optimized for deployment on an **AWS EC2 instance (Amazon Linux 2023)** connected to an **Amazon RDS MySQL database**.

---

## Key Features

1. **Analytical Dashboard**: Summarizes registry statistics dynamically using modern responsive cards with vibrant metrics.
2. **Interactive CRUD Ledger**: Create, view, update, and delete student entries.
3. **Database Fallback States**: Catches db errors gracefully, rendering troubleshooting steps for RDS configurations instead of crude 500 errors.
4. **Data Validation Controls**: Implements both interactive client-side checks and backend regex validation to block duplicate registration emails.
5. **Interactive Delete Modals**: Asks for consent before removing student files to avoid accidental deletion.
6. **Thread-Safe Pooling**: Leverages `mysql.connector.pooling` for scale-friendly database access.

---

## Directory Structure

```text
student-management-system/
│
├── static/
│   ├── script.js          # Form validation and dynamic modal handlers
│   └── style.css          # Core design tokens, gradients, and custom responsive tables
│
├── templates/
│   ├── layout.html        # Responsive Bootstrap base skeleton
│   ├── index.html         # Main dashboard list and search controls
│   ├── add_student.html   # Registry entry form
│   ├── edit_student.html  # Modify student form settings
│   └── db_error.html      # Troubleshooting panel for connection issues
│
├── app.py                 # Core routing, connection pooling, and CRUD logic
├── config.py              # Configuration manager (binds environment inputs with local fallbacks)
├── requirements.txt       # Python project packages list
├── schema.sql             # SQL instructions to build table and seed demonstration data
└── README.md              # Deployment guide (this file)
```

---

## Local Development Setup

To run this application locally, follow these steps:

### 1. Database Initialization
Ensure you have MySQL server running. Connect with root credentials and import the database layout:
```bash
mysql -u root -p < schema.sql
```
*Note: The script automatically creates the database `student_db` and seeds it with 5 sample students matching the required fields.*

### 2. Configure Credentials
Create a `.env` file at the project root folder or edit `config.py` to specify your database configurations:
```ini
SECRET_KEY=custom-key-for-local-runs
MYSQL_HOST=localhost
MYSQL_USER=your_mysql_username
MYSQL_PASSWORD=your_mysql_password
MYSQL_DB=student_db
MYSQL_PORT=3306
```

### 3. Setup Virtual Environment & Dependencies
Create a virtual environment, activate it, and install required libraries:
```bash
# Windows
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Run the Dev Server
Launch Flask:
```bash
python app.py
```
Open your browser and navigate to [http://localhost:5000](http://localhost:5000).

---

## Vercel Deployment Guide

This project includes `vercel.json` and `api/index.py`, so Vercel can run the Flask app through the Python serverless runtime.

### 1. Connect a Hosted MySQL Database
Vercel does not run MySQL inside the web app. Use a hosted MySQL database such as Amazon RDS, Aiven, Railway, PlanetScale, or another MySQL provider.

Run `schema.sql` on that database once, or let the app create the tables on the first request if your database user has create-table permissions.

### 2. Import the Project Into Vercel
1. Push this folder to GitHub.
2. Open Vercel and choose **Add New Project**.
3. Import the GitHub repository.
4. Keep the framework preset as **Other** if Flask is not auto-detected.
5. Deploy.

### 3. Add Environment Variables in Vercel
Open **Project Settings > Environment Variables** and add:

```ini
SECRET_KEY=replace-with-a-long-random-secret
MYSQL_HOST=your-hosted-mysql-host
MYSQL_USER=your-mysql-user
MYSQL_PASSWORD=your-mysql-password
MYSQL_DB=student_db
MYSQL_PORT=3306
MYSQL_POOL_SIZE=3
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-smtp-login-email
SMTP_PASSWORD=your-smtp-app-password
SMTP_SENDER=your-smtp-login-email
SMTP_USE_TLS=true
```

For Gmail, use an App Password instead of your normal Gmail password.

### 4. Redeploy
After saving the variables, redeploy the project from Vercel. The enrollment email will send when `SMTP_USER`, `SMTP_PASSWORD`, and the other SMTP variables are valid.

### 5. Database Access
Your MySQL provider must allow Vercel to connect to it. If the database uses IP restrictions, configure access for Vercel outbound connections or choose a serverless-friendly MySQL provider with public SSL connections.

---

## AWS Deployment Guide

This guide walks you through deploying this Flask app on an **AWS EC2 (Amazon Linux 2023)** server proxying connection to **Amazon RDS MySQL**.

### Phase A: Setup Amazon RDS MySQL
1. Go to the AWS RDS console and click **Create database**.
2. Select **MySQL** as engine type, choose **Free Tier** template if applicable.
3. Configure DBInstance identifier, Master username, and Master password. Save these credentials in a secure place.
4. Under **Connectivity**, configure:
   - **Public Access**: Select *No* if the EC2 web server will reside in the same VPC private subnet, or *Yes* if connecting externally.
   - **VPC Security Group**: Select/create a security group.
5. Create the database. Retrieve the **Endpoint URL** once setup stabilizes (e.g., `database-1.cwxyz.us-east-1.rds.amazonaws.com`).
6. **RDS Inbound Rules**: Edit the RDS security group and add an inbound rule:
   - **Type**: MYSQL/Aurora (3306)
   - **Source**: Select your EC2 Security Group ID, or your EC2 instance's private IP. This permits the Flask host to speak to the RDS instance.

### Phase B: Launch AWS EC2 Instance
1. Launch an EC2 instance using the **Amazon Linux 2023 AMI**.
2. Associate a Security Group enabling:
   - Port `22` (SSH access)
   - Port `5000` (or `80` if using Nginx reverse proxy)
3. Connect via SSH to the server.

### Phase C: System Packages & Application Install
Run the following terminal instructions on your EC2 host:

1. Update packages and install python 3.11:
   ```bash
   sudo dnf update -y
   sudo dnf install python3.11 python3.11-pip git -y
   ```

2. Clone/Upload your project files to `/var/www/student-management-system/` or your home directory (`/home/ec2-user/student-management-system/`):
   ```bash
   cd /home/ec2-user
   git clone <your-repository-url> student-management-system
   cd student-management-system
   ```

3. Setup environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Populate environment variables by writing a `.env` file inside the folder:
   ```bash
   cat <<EOF > .env
   SECRET_KEY=another-strong-production-key-here
   MYSQL_HOST=database-1.cwxyz.us-east-1.rds.amazonaws.com
   MYSQL_USER=rds_master_username
   MYSQL_PASSWORD=rds_master_password
   MYSQL_DB=student_db
   MYSQL_PORT=3306
   EOF
   ```

5. Seed RDS database by connecting. Since schema.sql has self-healing triggers inside app.py, the table structure and 5 mock records will automatically spawn in the RDS instance upon the first request!
   *Alternatively, seed it manually:*
   ```bash
   mysql -h database-1.cwxyz.us-east-1.rds.amazonaws.com -u rds_master_username -p student_db < schema.sql
   ```

### Phase D: Setup Systemd Service (Process Management)
Configure Systemd to manage Gunicorn running in the background and auto-reboot the process during OS restarts.

1. Create a systemd unit configuration file:
   ```bash
   sudo nano /etc/systemd/system/student-system.service
   ```

2. Paste the following configuration, correcting user names and paths if custom directories were used:
   ```ini
   [Unit]
   Description=Gunicorn instance running the Student Management System
   After=network.target

   [Service]
   User=ec2-user
   WorkingDirectory=/home/ec2-user/student-management-system
   Environment="PATH=/home/ec2-user/student-management-system/venv/bin"
   ExecStart=/home/ec2-user/student-management-system/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:5000 app:app

   [Install]
   WantedBy=multi-user.target
   ```

3. Enable and start the background daemon:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl start student-system
   sudo systemctl enable student-system
   ```

4. Check the service health:
   ```bash
   sudo systemctl status student-system
   ```

Your web service is now active and listening directly on port `5000`! Enter your EC2 instance's Public IPv4 address followed by `:5000` (e.g. `http://54.210.12.34:5000`) in any client browser to explore the live application.

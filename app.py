# Core structure for a phishing campaign simulator
from flask import Flask, render_template, request, redirect
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import sqlite3
import uuid
import datetime

app = Flask(__name__)
DB_PATH = "phishing_simulator.db"

# Database setup
def setup_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Campaign table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS campaigns (
        id TEXT PRIMARY KEY,
        name TEXT,
        description TEXT,
        template TEXT,
        created_at TIMESTAMP
    )
    ''')
    
    # Targets table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS targets (
        id TEXT PRIMARY KEY,
        campaign_id TEXT,
        email TEXT,
        name TEXT,
        department TEXT,
        unique_token TEXT,
        FOREIGN KEY (campaign_id) REFERENCES campaigns (id)
    )
    ''')
    
    # Events table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS events (
        id TEXT PRIMARY KEY,
        target_id TEXT,
        event_type TEXT,  -- email_opened, link_clicked, credentials_entered
        timestamp TIMESTAMP,
        ip_address TEXT,
        user_agent TEXT,
        FOREIGN KEY (target_id) REFERENCES targets (id)
    )
    ''')
    
    conn.commit()
    conn.close()

# Campaign management
def create_campaign(name, description, template):
    campaign_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO campaigns VALUES (?, ?, ?, ?, ?)",
        (campaign_id, name, description, template, datetime.datetime.now())
    )
    
    conn.commit()
    conn.close()
    return campaign_id

def add_target(campaign_id, email, name, department):
    target_id = str(uuid.uuid4())
    unique_token = str(uuid.uuid4())
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO targets VALUES (?, ?, ?, ?, ?, ?)",
        (target_id, campaign_id, email, name, department, unique_token)
    )
    
    conn.commit()
    conn.close()
    return target_id, unique_token

# Email sending (simplified - would need actual SMTP configuration)
def send_phishing_email(target_id, template_name=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT t.email, t.name, t.unique_token, c.template FROM targets t JOIN campaigns c ON t.campaign_id = c.id WHERE t.id = ?",
        (target_id,)
    )
    
    target_data = cursor.fetchone()
    conn.close()
    
    if not target_data:
        return False
    
    email, name, token, template = target_data
    tracking_pixel = f"<img src='http://localhost:5000/track/{token}/open' width='1' height='1' />"
    phishing_link = f"http://localhost:5000/login/{token}"
    
    # Replace placeholders in template
    email_content = template.replace("{{name}}", name)
    email_content = email_content.replace("{{phishing_link}}", phishing_link)
    email_content += tracking_pixel

    # === ACTUAL EMAIL SENDING ===
    sender_email = "datasectesting@outlook.com"         # Replace with your real email
    sender_password = "datasec@testing"    # Use an app password or store it safely
    smtp_server = "smtp.office365.com"
    smtp_port = 587

    try:
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = email
        msg["Subject"] = "Important Security Notification"
        msg.attach(MIMEText(email_content, "html"))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()

        print(f"Email sent to {email}")
        return True

    except Exception as e:
        print(f"Failed to send email to {email}: {e}")
        return False

# def send_phishing_email(target_id, template_name):
#     conn = sqlite3.connect(DB_PATH)
#     cursor = conn.cursor()
    
#     cursor.execute(
#         "SELECT t.email, t.name, t.unique_token, c.template FROM targets t JOIN campaigns c ON t.campaign_id = c.id WHERE t.id = ?",
#         (target_id,)
#     )
    
#     target_data = cursor.fetchone()
#     conn.close()
    
#     if not target_data:
#         return False
    
#     email, name, token, template = target_data
#     tracking_pixel = f"<img src='http://yourserver.com/track/{token}/open' width='1' height='1' />"
#     phishing_link = f"http://yourserver.com/login/{token}"
    
#     # Replace placeholders in template
#     email_content = template.replace("{{name}}", name)
#     email_content = email_content.replace("{{phishing_link}}", phishing_link)
#     email_content += tracking_pixel
    
#     # Send email (placeholder - implement with actual SMTP)
#     print(f"Would send email to {email} with token {token}")
#     return True

# Tracking endpoints
@app.route('/track/<token>/open')
def track_open(token):
    # Record email open event
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM targets WHERE unique_token = ?", (token,))
    target = cursor.fetchone()
    
    if target:
        event_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?)",
            (event_id, target[0], "email_opened", datetime.datetime.now(), 
             request.remote_addr, request.user_agent.string)
        )
        conn.commit()
    
    conn.close()
    
    # Return a 1x1 transparent pixel
    return app.send_static_file('pixel.gif')

@app.route('/login/<token>')
def fake_login(token):
    # Record link click event
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM targets WHERE unique_token = ?", (token,))
    target = cursor.fetchone()
    
    if target:
        event_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?)",
            (event_id, target[0], "link_clicked", datetime.datetime.now(), 
             request.remote_addr, request.user_agent.string)
        )
        conn.commit()
    
    conn.close()
    
    # Show a fake login page based on the campaign template
    return render_template('fake_login.html', token=token)

@app.route('/submit_credentials/<token>', methods=['POST'])
def submit_credentials(token):
    # Record credential submission event (but don't store actual credentials)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM targets WHERE unique_token = ?", (token,))
    target = cursor.fetchone()
    
    if target:
        event_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?)",
            (event_id, target[0], "credentials_entered", datetime.datetime.now(), 
             request.remote_addr, request.user_agent.string)
        )
        conn.commit()
    
    conn.close()
    
    # Redirect to education page
    return redirect(f'/education/{token}')

@app.route('/education/<token>')
def education(token):
    # Show educational content about phishing awareness
    return render_template('education.html', token=token)

# Admin dashboard routes would be added here
@app.route('/admin/view_campaign/<campaign_id>')
def view_campaign(campaign_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
    campaign = cursor.fetchone()
    
    cursor.execute("SELECT * FROM targets WHERE campaign_id = ?", (campaign_id,))
    targets = cursor.fetchall()
    
    # Get event data for each target
    for i, target in enumerate(targets):
        cursor.execute("""
            SELECT event_type, timestamp FROM events 
            WHERE target_id = ? 
            ORDER BY timestamp
        """, (target['id'],))
        events = cursor.fetchall()
        targets[i] = dict(target)
        targets[i]['events'] = events
    
    conn.close()
    return render_template('admin/view_campaign.html', campaign=campaign, targets=targets)

@app.route('/admin/add_target/<campaign_id>', methods=['GET', 'POST'])
def add_target_db(campaign_id):
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        department = request.form.get('department')
        
        target_id, _ = add_target(campaign_id, email, name, department)
        return redirect(f'/admin/view_campaign/{campaign_id}')
    
    return render_template('admin/add_target.html', campaign_id=campaign_id)

@app.route('/admin/send_email/<target_id>')
def send_email_to_target(target_id):
    success = send_phishing_email(target_id, None)  # Template is retrieved from DB
    if success:
        return redirect('/admin')
    return "Error sending email", 500

# Admin routes
@app.route('/admin')
def admin_dashboard():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM campaigns")
    campaigns_raw = cursor.fetchall()
    
    campaigns = []
    for campaign in campaigns_raw:
        # Get statistics
        cursor.execute("SELECT COUNT(*) FROM targets WHERE campaign_id = ?", (campaign['id'],))
        target_count = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT target_id) as opened
            FROM events
            JOIN targets ON events.target_id = targets.id
            WHERE targets.campaign_id = ? AND events.event_type = 'email_opened'
        """, (campaign['id'],))
        opened = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT target_id) as clicked
            FROM events
            JOIN targets ON events.target_id = targets.id
            WHERE targets.campaign_id = ? AND events.event_type = 'link_clicked'
        """, (campaign['id'],))
        clicked = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT target_id) as submitted
            FROM events
            JOIN targets ON events.target_id = targets.id
            WHERE targets.campaign_id = ? AND events.event_type = 'credentials_entered'
        """, (campaign['id'],))
        submitted = cursor.fetchone()[0]
        
        open_rate = (opened / target_count * 100) if target_count > 0 else 0
        click_rate = (clicked / target_count * 100) if target_count > 0 else 0
        success_rate = (submitted / target_count * 100) if target_count > 0 else 0
        
        campaigns.append({
            'id': campaign['id'],
            'name': campaign['name'],
            'description': campaign['description'],
            'created_at': campaign['created_at'],
            'targets': target_count,
            'open_rate': round(open_rate, 1),
            'click_rate': round(click_rate, 1),
            'success_rate': round(success_rate, 1)
        })
    
    conn.close()
    return render_template('admin/dashboard.html', campaigns=campaigns)

@app.route('/admin/new_campaign', methods=['GET', 'POST'])
def new_campaign():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        template_name = request.form.get('template')
        
        # Read template file
        with open(f'templates/emails/{template_name}', 'r') as f:
            template_content = f.read()
        
        # Create campaign
        create_campaign(name, description, template_content)
        return redirect('/admin')
    
    # Get available templates
    import os
    templates = [f for f in os.listdir('templates/emails') if f.endswith('.html')]
    
    return render_template('admin/campaign_creator.html', templates=templates)

if __name__ == '__main__':
    setup_database()
    app.run(debug=True)
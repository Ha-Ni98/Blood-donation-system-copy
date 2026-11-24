# Blood Bank Management System

A web application that connects blood donors, patients and a blood bank administrator. Patients request blood, donors offer to donate, and the administrator matches requests with donors and stock, tracks each request through its lifecycle, and manages users and donor eligibility.

Built with Django as a final-year project.

> This repository includes a V1 and a V2 of the application. V2 is the current version and the one to run.

## Features

**Patients**
- Create a patient profile and submit blood requests (blood type, units, urgency, required date, reason, location)
- Follow the status of each request, and cancel a request before it is approved
- Register as a donor from a patient account, and the reverse

**Donors**
- Create a donor profile with blood type and last donation date
- Offer a donation, which the administrator approves, completes or cancels
- Check donor eligibility, and register as a patient from a donor account

**Administrator**
- Dashboard with an overview of requests, donations and stock
- Manage blood stock by blood type
- Approve a blood request by attributing units from stock, complete it, or reject it
- Approve, complete or cancel donation offers
- Review donor eligibility and manage users (edit and delete)

**General**
- Blood compatibility: a request is matched with donors and stock of compatible blood types
- Notifications for users when a request or donation changes status
- Wilaya and commune selection, loaded from data and served by an API endpoint
- Interface in English, French and Arabic

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python, Django 3.0 |
| Database | SQLite (development) |
| Frontend | Django templates, static CSS and JavaScript |
| Internationalisation | Django `i18n` with `locale/` for English, French and Arabic |
| Forms | `django-widget-tweaks` for form rendering |

## Project structure

```
V1/                         first version of the application
V2/                         current version
  blood/                    blood requests, stock, notifications, admin views, management commands
  donor/                    donor-facing pages and donation offers
  patient/                  patient-facing pages
  bloodbankmanagement/      project settings and root URL configuration
  templates/                HTML templates
  static/                   CSS, JavaScript, images
  locale/                   translations (en, fr, ar)
  requirements.txt          pinned Python dependencies
```

## Getting started

Prerequisites: Python 3.8 or 3.9. Django 3.0 does not support newer Python versions.

Run the following from the `V2` folder.

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create the database tables
python manage.py migrate

# 4. Load wilayas and communes
python manage.py load_wilayas

# 5. Load blood types and initial stock
python manage.py load_blood_data

# 6. Create an administrator account
python manage.py createsuperuser

# 7. Start the development server
python manage.py runserver
```

Then open http://127.0.0.1:8000/ in your browser.

### Configuration

Settings live in `V2/bloodbankmanagement/settings.py`. Before running the project anywhere other than your own machine, move these values out of the source code into environment variables:

- `SECRET_KEY`: generate a new one for your installation
- `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD`: the account used to send notification emails
- `EMAIL_RECEIVING_USER`: the address that receives messages sent from the website

Email sending uses Gmail SMTP by default. The placeholder values in the file are not real credentials, so emails will not be sent until you configure your own account.

## Running the tests

```bash
cd V2
python manage.py test
```

The test suite covers the blood, donor and patient apps.

## Known limitations

This is an academic project, so a few things are deliberately simple:

- **Django 3.0** is end-of-life and no longer receives security updates. Upgrading to a supported LTS release is the first improvement to make.
- **SQLite** is used for development. A production deployment would use PostgreSQL or MySQL.
- **Debug mode** is on in the settings file, and `ALLOWED_HOSTS` is empty. Both must be changed before any public deployment.
- **Settings contain values committed to source control.** Move secrets to environment variables before publishing.
- **Email** depends on a real SMTP account, which must be configured by the user.

## Possible next steps

- Upgrade Django and move to a production database
- Move all secrets to environment variables and deploy behind HTTPS
- Add an API for a mobile client
- Expand automated test coverage for the approval and attribution workflow

## License

Released under the MIT License. See [LICENSE](LICENSE).

## Author

Built by me as a final-year project to help my friend, with the help of Claude Code.

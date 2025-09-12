# 🍽️ Restaurant Audit System

A comprehensive Frappe-based application for managing restaurant inspections, hygiene checks, and operational audits across franchise locations. This system ensures quality control, compliance monitoring, and consistent operational standards.

## 📋 Table of Contents

- [Features](#-features)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [User Guide](#-user-guide)
- [API Documentation](#-api-documentation)
- [Development](#-development)
- [Contributing](#-contributing)
- [License](#-license)

## ✨ Features

### 🏪 Restaurant Management
- **Location Tracking**: GPS coordinates with configurable radius settings
- **Employee Assignment**: Link auditors and managers to specific restaurants
- **Restaurant Profiles**: Complete restaurant information and contact details

### 🔍 Audit System
- **Structured Checklists**: Customizable audit templates and questions
- **Scoring System**: Automated calculation of scores and compliance ratings
- **Image Attachments**: Photo evidence for audit findings
- **Comments & Recommendations**: Detailed feedback and action items
- **Real-time Validation**: Form validation and progress tracking

### 📅 Scheduling & Automation
- **Weekly Audit Scheduling**: Automated visit planning
- **Status Tracking**: Pending → Completed → Overdue workflow
- **Email Notifications**: Automated alerts for auditors and managers
- **Overdue Management**: Automatic escalation of missed audits

### 📊 Reporting & Analytics
- **Audit Dashboards**: Visual progress tracking
- **Score Analytics**: Performance trends and compliance metrics
- **Export Capabilities**: Data export for external analysis
- **Compliance Reports**: Management-level reporting

### 👥 User Management
- **Role-based Access**: System Manager, Employee, and Auditor roles
- **Custom Authentication**: Dedicated login system for auditors
- **Permission Control**: Granular access management

## 🚀 Installation

### Prerequisites
- Frappe Framework (v14+)
- Python 3.8+
- Node.js 14+
- MySQL/MariaDB

### Install the App

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd restaurant_audit
   ```

2. **Install in your Frappe bench**:
   ```bash
   bench get-app restaurant_audit
   bench install-app restaurant_audit
   ```

3. **Run database migrations**:
   ```bash
   bench migrate
   ```

4. **Restart your Frappe server**:
   ```bash
   bench restart
   ```

## ⚙️ Configuration

### 1. User Roles Setup

Create the following user roles in your Frappe system:
- **Auditor**: Can conduct audits and view assigned restaurants
- **Restaurant Manager**: Can view audit results for their restaurants
- **System Manager**: Full access to all features

### 2. Restaurant Setup

1. Navigate to **Restaurant Audit > Restaurant**
2. Create restaurant records with:
   - Restaurant name and address
   - GPS coordinates (latitude/longitude)
   - Location radius for geofencing
   - Assigned restaurant manager
   - Assigned auditors/employees

### 3. Audit Templates

1. Go to **Restaurant Audit > Checklist Template**
2. Create audit templates with:
   - Template name and description
   - Categories and questions
   - Scoring criteria
   - Required fields

### 4. Scheduled Jobs

The app includes automated weekly audit checks. Ensure the scheduler is running:
```bash
bench schedule
```

## 📖 User Guide

### For Auditors

#### 1. Login
- Navigate to `/audit-login`
- Enter your email and password
- Access the restaurant selection dashboard

#### 2. Conducting an Audit
1. Select a restaurant from the dashboard
2. Click "Start Audit" to open the audit form
3. Complete all required questions
4. Add photos and comments as needed
5. Submit the audit for review

#### 3. Viewing Results
- Access completed audits from the dashboard
- View scores and recommendations
- Track audit history

### For Restaurant Managers

#### 1. Dashboard Access
- Login to the main Frappe system
- Navigate to **Restaurant Audit** module
- View assigned restaurants and audit results

#### 2. Monitoring
- Track audit completion status
- Review scores and recommendations
- Respond to audit findings

### For System Administrators

#### 1. Restaurant Management
- Add/edit restaurant locations
- Assign managers and auditors
- Configure location settings

#### 2. Template Management
- Create and modify audit templates
- Set up scoring criteria
- Manage question categories

#### 3. User Management
- Create user accounts
- Assign roles and permissions
- Monitor system usage

## 🔌 API Documentation

### REST API Endpoints

#### Get Restaurants
```http
GET /api/method/restaurant_audit.api.get_restaurants
```

#### Submit Audit
```http
POST /api/method/restaurant_audit.api.submit_audit
Content-Type: application/json

{
    "restaurant": "REST-001",
    "auditor": "auditor@example.com",
    "audit_date": "2024-01-15",
    "answers": [...]
}
```

#### Get Audit History
```http
GET /api/method/restaurant_audit.api.get_audit_history
```

### Web Routes

- `/audit-login` - Auditor login page
- `/audit-restaurants` - Restaurant selection dashboard
- `/audit-form` - Audit form interface

## 🛠️ Development

### Project Structure
```
restaurant_audit/
├── restaurant_audit/
│   ├── doctype/           # Data models
│   ├── api/              # API endpoints
│   ├── www/              # Web pages
│   └── templates/        # Jinja2 templates
├── hooks.py              # App configuration
├── tasks.py              # Scheduled tasks
└── README.md
```

### Key DocTypes

- **Restaurant**: Restaurant information and location data
- **Audit Submission**: Main audit records
- **Scheduled Audit Visit**: Planned audit visits
- **Audit Question**: Individual audit questions
- **Checklist Template**: Reusable audit templates

### Customization

#### Adding New Audit Questions
1. Navigate to **Restaurant Audit > Audit Question**
2. Create new question records
3. Add to checklist templates
4. Questions will appear in audit forms

#### Custom Scoring
Modify the scoring logic in `restaurant_audit/restaurant_audit/doctype/audit_submission/audit_submission.py`

#### UI Customization
Edit the HTML/CSS files in the `www/` directory:
- `audit-login.html` - Login page
- `audit-restaurants.html` - Dashboard
- `audit-form.html` - Audit form

## 📊 Monitoring & Maintenance

### Scheduled Tasks
- **Weekly Audit Check**: Runs every Monday to check for missing audits
- **Overdue Notifications**: Sends alerts for overdue audits
- **Email Reminders**: Automated notifications to auditors and managers

### Database Maintenance
```bash
# Backup database
bench backup

# Optimize database
bench mariadb optimize

# Check for errors
bench doctor
```

### Logs
Monitor application logs:
```bash
bench logs
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow Frappe coding standards
- Add tests for new features
- Update documentation
- Ensure backward compatibility

## 📝 Changelog

### Version 1.0.0
- Initial release
- Basic audit functionality
- Restaurant management
- Scheduling system
- Email notifications

## 🐛 Troubleshooting

### Common Issues

#### Login Problems
- Verify user credentials in Frappe User doctype
- Check user roles and permissions
- Ensure user is linked to Employee record

#### Audit Form Not Loading
- Check browser console for JavaScript errors
- Verify user has proper permissions
- Clear browser cache

#### Email Notifications Not Working
- Verify email settings in Frappe
- Check scheduled job status
- Review error logs

### Support
For technical support, please:
1. Check the troubleshooting section
2. Review Frappe documentation
3. Create an issue in the repository

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](license.txt) file for details.

## 🙏 Acknowledgments

- Built on the [Frappe Framework](https://frappeframework.com/)
- Inspired by modern audit management systems
- Community contributions and feedback

---

**Restaurant Audit System** - Ensuring quality and compliance across your restaurant network. 🍽️✨
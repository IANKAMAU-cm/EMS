from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from forms import EmployeeForm, EmployeeLoginForm, ManagerLoginForm, AdminLoginForm, RegistrationForm, ManagerRegistrationForm, AdminRegistrationForm, LeaveRequestForm, LeaveApprovalForm, JobPostingForm, ApplicationForm, OnboardingForm
from models import Employee, User, LeaveRequest, JobPosting, Application
from functools import wraps
from flask import abort
from flask_login import current_user
from extensions import db


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function

def manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_manager():
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function

def employee_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_employee():
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///employees.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_employee'  # Default login view

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def dashboard():
    employees = Employee.query.all()
    return render_template('employee_dashboard.html', employees=employees)


@app.route('/register/employee', methods=['GET', 'POST'])
def register_employee():
    form = RegistrationForm()  # Create an instance of the registration form
    if form.validate_on_submit():
        # Create new User object
        user = User(
            username=form.username.data,
            email=form.email.data,  # Set the email field
            role='Employee'  # Set role to Employee by default
        )
        user.set_password(form.password.data)  # Hash the password

        # Create an Employee object with additional details
        employee = Employee(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            job_title=form.job_title.data,
            department=form.department.data,
            hire_date=form.hire_date.data
        )

        # Add both User and Employee to the database
        db.session.add(user)
        db.session.commit()  # Commit user first to get user.id
        employee.user_id = user.id  # Link employee to user
        db.session.add(employee)
        db.session.commit()

        flash('Registration successful! You can now log in.')
        return redirect(url_for('login_employee'))  # Redirect to employee login
    return render_template('register_employee.html', form=form)


@app.route('/login/employee', methods=['GET', 'POST'])
def login_employee():
    form = EmployeeLoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data) and user.is_employee():
            login_user(user)
            return redirect(url_for('employee_dashboard'))
        else:
            flash('Invalid username or password for employee.')
    return render_template('login_employee.html', form=form)


# Employee: Request leave
@app.route('/employee/request_leave', methods=['GET', 'POST'])
@login_required
def request_leave():
    form = LeaveRequestForm()
    if form.validate_on_submit():
        leave_request = LeaveRequest(
            employee_id=current_user.id,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            reason=form.reason.data
        )
        db.session.add(leave_request)
        db.session.commit()
        flash('Leave request submitted successfully!', 'success')
        return redirect(url_for('employee_dashboard'))
    
    else:
        print(form.errors)  # Log form errors for debugging

    return render_template('request_leave.html', form=form)


@app.route('/login/manager', methods=['GET', 'POST'])
def login_manager():
    form = ManagerLoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data) and user.is_manager():
            login_user(user)
            return redirect(url_for('manager_dashboard'))
        else:
            flash('Invalid username or password for manager.')
    return render_template('login_manager.html', form=form)


# Manager: View and manage leave requests
@app.route('/manager/leave_requests', methods=['GET', 'POST'])
@login_required
def manage_leave_requests():
    # Ensure only managers can access this
    if current_user.role != 'Manager':
        return redirect(url_for('employee_dashboard'))

    leave_requests = LeaveRequest.query.filter_by(status='Pending').all()
    return render_template('manage_leave_requests.html', leave_requests=leave_requests)

# Manager: Approve or reject a leave request
@app.route('/manager/approve_leave/<int:request_id>', methods=['GET', 'POST'])
@login_required
def approve_leave(request_id):
    leave_request = LeaveRequest.query.get_or_404(request_id)
    form = LeaveApprovalForm()

    if form.validate_on_submit():
        leave_request.status = form.status.data
        leave_request.response_message = form.response_message.data
        leave_request.manager_id = current_user.id
        db.session.commit()
        flash(f'Leave request has been {form.status.data.lower()}ed.', 'success')
        return redirect(url_for('manage_leave_requests'))
    
    return render_template('approve_leave.html', leave_request=leave_request, form=form)


@app.route('/create_job', methods=['GET', 'POST'])
def create_job():
    form = JobPostingForm()
    if form.validate_on_submit():
        job = JobPosting(
            job_title=form.job_title.data,
            job_description=form.job_description.data,
            requirements=form.requirements.data
        )
        db.session.add(job)
        db.session.commit()
        flash('Job posted successfully!', 'success')
        return redirect(url_for('job_list'))
    return render_template('create_job.html', form=form)


@app.route('/job_list')
def job_list():
    jobs = JobPosting.query.all()
    return render_template('job_list.html', jobs=jobs)

@app.route('/apply_job/<int:job_id>', methods=['GET', 'POST'])
def apply_job(job_id):
    job = JobPosting.query.get_or_404(job_id)
    form = ApplicationForm()
    if form.validate_on_submit():
        application = Application(
            job_id=job.id,
            applicant_name=form.applicant_name.data,
            email=form.email.data,
            resume=form.resume.data
        )
        db.session.add(application)
        db.session.commit()
        flash('Application submitted successfully!', 'success')
        return redirect(url_for('job_list'))
    return render_template('apply_job.html', form=form, job=job)


@app.route('/onboarding/<int:employee_id>', methods=['GET', 'POST'])
def onboarding(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    form = OnboardingForm()
    if form.validate_on_submit():
        # Process onboarding form data
        employee.bank_details = form.bank_details.data
        employee.emergency_contact = form.emergency_contact.data
        db.session.commit()
        flash('Onboarding completed successfully!', 'success')
        return redirect(url_for('employee_dashboard'))
    return render_template('onboarding.html', employee_name=employee.name, form=form)


@app.route('/manager/view_applications/<int:job_id>')
def view_applications(job_id):
    job = JobPosting.query.get_or_404(job_id)
    applications = Application.query.filter_by(job_id=job_id).all()
    return render_template('view_applications.html', job=job, applications=applications)


@app.route('/login/admin', methods=['GET', 'POST'])
def login_admin():
    form = AdminLoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data) and user.is_admin():
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password for admin.')
    return render_template('login_admin.html', form=form)


@app.route('/register_manager', methods=['GET', 'POST'])
def register_manager():
    form = ManagerRegistrationForm()
    if form.validate_on_submit():
        manager = User(username=form.username.data, email=form.email.data, role='Manager')
        manager.set_password(form.password.data)
        db.session.add(manager)
        db.session.commit()
        flash('Manager account created successfully!', 'success')
        return redirect(url_for('login_manager'))
    return render_template('register_manager.html', form=form)

@app.route('/register_admin', methods=['GET', 'POST'])
def register_admin():
    form = AdminRegistrationForm()
    if form.validate_on_submit():
        admin = User(username=form.username.data, email=form.email.data, role='Admin')
        admin.set_password(form.password.data)
        db.session.add(admin)
        db.session.commit()
        flash('Admin account created successfully!', 'success')
        return redirect(url_for('login_admin'))
    return render_template('register_admin.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out')
    return redirect(url_for('login_employee'))  # Redirect to employee login

@app.route('/add_employee', methods=['GET', 'POST'])
@login_required
def add_employee():
    form = EmployeeForm()
    if form.validate_on_submit():
        employee = Employee(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            job_title=form.job_title.data,
            department=form.department.data,
            hire_date=form.hire_date.data
        )
        db.session.add(employee)
        db.session.commit()
        flash('Employee added successfully')
        return redirect(url_for('dashboard'))
    return render_template('employee.html', form=form)

@app.route('/admin_dashboard')
@login_required
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/manager_dashboard')
@login_required
@manager_required
def manager_dashboard():
    jobs = JobPosting.query.all()  # Retrieve all job postings from the databases
    return render_template('manager_dashboard.html', jobs=jobs)

@app.route('/employee_dashboard')
@login_required
@employee_required
def employee_dashboard():
    leave_requests = LeaveRequest.query.filter_by(employee_id=current_user.id).all()
    serialized_requests = [
        {
            "id": leave.id,
            "start_date": leave.start_date.strftime('%Y-%m-%d'),
            "end_date": leave.end_date.strftime('%Y-%m-%d'),
            "status": leave.status,
            "response_message": leave.response_message
        }
        for leave in leave_requests
    ]
    return render_template('employee_dashboard.html', leave_requests=serialized_requests)

if __name__ == '__main__':
    with app.app_context():
        #db.drop_all()
        db.create_all()
    app.run(debug=True)

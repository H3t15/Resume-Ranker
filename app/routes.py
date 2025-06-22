from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file, current_app
from flask_login import login_required, current_user
import os
from werkzeug.utils import secure_filename
from app.resume_utils import process_resumes
from io import BytesIO  # Change from StringIO to BytesIO
import pandas as pd
from app import db
from .user import Job, ResumeUpload, User

main_bp = Blueprint('main', __name__)

UPLOAD_FOLDER = ''

@main_bp.before_app_request
def before_request():
    global UPLOAD_FOLDER
    UPLOAD_FOLDER = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@main_bp.route('/')
def home():
    return render_template('home.html')

# ADMIN DASHBOARD - list jobs + add job
@main_bp.route('/admin/dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        title = request.form['title'].strip()
        description = request.form['description'].strip()

        if not title or not description:
            flash('Both Title and Description are required.', 'warning')
            return redirect(url_for('main.admin_dashboard'))

        job = Job(title=title, description=description, created_by=current_user.id)
        db.session.add(job)
        db.session.commit()
        flash(f'Job "{title}" added successfully.', 'success')
        return redirect(url_for('main.admin_dashboard'))

    jobs = Job.query.order_by(Job.created_at.desc()).all()
    return render_template('admin_dashboard.html', jobs=jobs)

# USER DASHBOARD - select job and upload resumes
@main_bp.route('/user/dashboard', methods=['GET', 'POST'])
@login_required
def user_dashboard():
    if current_user.role != 'user':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.home'))

    jobs = Job.query.order_by(Job.created_at.desc()).all()
    if not jobs:
        flash('No job postings available at the moment. Please check back later.', 'info')
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        job_id = request.form.get('job_id')
        if not job_id:
            flash('Please select a job first.', 'warning')
            return redirect(url_for('main.user_dashboard'))
        job = Job.query.get(job_id)
        if not job:
            flash('Selected job does not exist.', 'danger')
            return redirect(url_for('main.user_dashboard'))

        files = request.files.getlist('resumes')
        if not files or files[0].filename == '':
            flash('Please upload at least one resume PDF.', 'warning')
            return redirect(url_for('main.user_dashboard'))

        saved_paths = []
        upload_records = []

        for file in files:
            filename_raw = secure_filename(file.filename)
            if not filename_raw.lower().endswith('.pdf'):
                flash('Only PDF files are accepted.', 'warning')
                continue
            save_path = os.path.join(UPLOAD_FOLDER, filename_raw)

            # Prevent overwriting by adding suffix if needed
            count = 1
            base_name, ext = os.path.splitext(filename_raw)
            while os.path.exists(save_path):
                filename_raw = f"{base_name}_{count}{ext}"
                save_path = os.path.join(UPLOAD_FOLDER, filename_raw)
                count += 1

            file.save(save_path)
            saved_paths.append(save_path)

        if not saved_paths:
            flash('No valid PDF files uploaded.', 'danger')
            return redirect(url_for('main.user_dashboard'))

        ranked_results = process_resumes(saved_paths, job.description)

        # Save results to DB
        for res in ranked_results:
            upload_record = ResumeUpload(
                filename=res['name'],
                user_id=current_user.id,
                job_id=job.id,
                skills=res['skills'],
                experience=res['experience'],
                score=res['score']
            )
            db.session.add(upload_record)
            upload_records.append(upload_record)

        db.session.commit()

        # Store latest upload IDs to session for results display and CSV export
        session['latest_upload_ids'] = [u.id for u in upload_records]

        return redirect(url_for('main.upload_results'))

    return render_template('user_dashboard.html', jobs=jobs)

@main_bp.route('/upload/results')
@login_required
def upload_results():
    ids = session.get('latest_upload_ids')
    if not ids:
        flash('No recent upload results to display.', 'info')
        return redirect(url_for('main.user_dashboard'))

    resumes = ResumeUpload.query.filter(ResumeUpload.id.in_(ids)).all()
    return render_template('results.html', ranked_results=resumes)

# Ranked session - viewing all uploaded resumes & scores by users (admin) or own uploads (user)
@main_bp.route('/ranked')
@login_required
def ranked_session():
    if current_user.role == 'admin':
        # admin sees all resumes
        all_resumes = ResumeUpload.query.order_by(ResumeUpload.uploaded_at.desc()).all()
    else:
        # users see only their uploads
        all_resumes = ResumeUpload.query.filter_by(user_id=current_user.id).order_by(ResumeUpload.uploaded_at.desc()).all()

    # Get unique job titles from the database
    unique_jobs = db.session.query(Job.title).distinct().all()
    unique_jobs = [job[0] for job in unique_jobs]

    return render_template('results.html',
                         ranked_results=all_resumes,
                         unique_jobs=unique_jobs)

# Download CSV of all uploads (filtered by user role)
@main_bp.route('/download')
@login_required
def download_results():
    if current_user.role == 'admin':
        resumes = ResumeUpload.query.order_by(ResumeUpload.uploaded_at.desc()).all()
    else:
        resumes = ResumeUpload.query.filter_by(user_id=current_user.id).order_by(ResumeUpload.uploaded_at.desc()).all()

    if not resumes:
        flash('No resume data available for CSV download.', 'warning')
        if current_user.role == 'admin':
            return redirect(url_for('main.admin_dashboard'))
        else:
            return redirect(url_for('main.user_dashboard'))

    data = []
    for r in resumes:
        data.append({
            'Filename': r.filename,
            'User  ': r.user.username,
            'Job Title': r.job.title,
            'Skills': r.skills,
            'Experience (Years)': r.experience,
            'Score': r.score,
            'Uploaded At': r.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')
        })

    df = pd.DataFrame(data)

    # Use BytesIO instead of StringIO
    csv_buffer = BytesIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    return send_file(
        csv_buffer,
        mimetype='text/csv',
        as_attachment=True,
        download_name='resume_rankings.csv'
    )

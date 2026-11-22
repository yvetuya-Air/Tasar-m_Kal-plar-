"""Ödünç ekranı, yönetici işlemleri ve yazma yapmayan Strategy simülatörü."""
from datetime import timedelta
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from database import get_db
from security import login_required, role_required
from services import loan_service
from services.validation import requested_page

bp = Blueprint('loans',__name__,url_prefix='/odunc')


@bp.get('')
@login_required
def index():
    status = request.args.get('status','active')
    if status not in ('active','returned','all'):
        abort(400)
    page = requested_page(request.args.get('page',1))
    member = get_db().execute('SELECT id FROM members WHERE user_id=?',(g.user.id,)).fetchone() if g.user.role=='member' else None
    items,count,page,pages = loan_service.list_loans(member['id'] if member else None,g.user.role=='member',status,page)
    return render_template('loans.html',items=items,count=count,page=page,pages=pages,status=status,today=loan_service.today().isoformat())


@bp.route('/ver',methods=['GET','POST'])
@role_required('admin')
def borrow():
    data = request.form if request.method=='POST' else {'due_on':(loan_service.today()+timedelta(days=14)).isoformat(),
                                                        'member_id': request.args.get('member_id', '')}
    error = None
    if request.method=='POST':
        try:
            loan_service.borrow_book(request.form.get('book_id',''),request.form.get('member_id',''),request.form.get('due_on',''),g.user.id)
        except loan_service.LoanValidationError as problem:
            error = str(problem)
        else:
            flash('Kitap ödünç verildi.','success')
            return redirect(url_for('loans.index'))
    books,members = loan_service.borrowing_choices()
    return render_template('loan_form.html',books=books,members=members,data=data,error=error,today=loan_service.today().isoformat()),422 if error else 200


@bp.route('/<int:loan_id>/iade',methods=['GET','POST'])
@role_required('admin')
def return_book(loan_id):
    row = loan_service.loan_details(loan_id)
    if row is None:
        abort(404)
    error = None
    if request.method=='POST':
        try:
            loan_service.return_loan(loan_id,g.user.id)
        except LookupError:
            abort(404)
        except loan_service.LoanValidationError as problem:
            error = str(problem)
        else:
            flash('İade kaydedildi; kesin gecikme cezası hesaplandı.','success')
            return redirect(url_for('loans.index',status='returned'))
    days,amount = (0,0) if row['returned_on'] else loan_service.penalty_for(row['member_type'],loan_service.parse_date(row['due_on']),loan_service.today())
    return render_template('loan_return.html',row=row,error=error,days=days,amount=amount,today=loan_service.today().isoformat()),409 if error else 200


@bp.post('/<int:loan_id>/yenile')
@login_required
def renew(loan_id):
    try:
        loan_service.renew_loan(loan_id, g.user)
    except LookupError:
        abort(404)
    except loan_service.LoanValidationError as error:
        flash(str(error), 'error')
    else:
        flash('Ödünç süresi uzatıldı.', 'success')
    return redirect(url_for('loans.index'))


@bp.route('/simulator',methods=['GET','POST'])
@login_required
def simulator():
    data = request.form if request.method=='POST' else {'member_type':'student','due_on':loan_service.today().isoformat(),'returned_on':loan_service.today().isoformat()}
    error = None
    result = None
    if request.method=='POST':
        try:
            days,amount = loan_service.penalty_for(data.get('member_type',''),loan_service.parse_date(data.get('due_on','')),loan_service.parse_date(data.get('returned_on','')))
            result = {'days':days,'amount':amount}
        except loan_service.LoanValidationError as problem:
            error = str(problem)
    return render_template('penalty_simulator.html',data=data,error=error,result=result),422 if error else 200

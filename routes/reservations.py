"""Rezervasyon formları, kişisel liste ve sunucu sahiplik denetimi."""
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from security import login_required
from services import reservation_service
from services.notification_service import member_for_user
from services.validation import requested_page

bp = Blueprint('reservations',__name__,url_prefix='/rezervasyonlar')


@bp.get('')
@login_required
def index():
    status = request.args.get('status','active')
    if status not in ('active','history','all'):
        abort(400)
    page = requested_page(request.args.get('page',1))
    items,count,page,pages = reservation_service.list_reservations(member_for_user(g.user.id),g.user.role!='admin',status,page)
    return render_template('reservations.html',items=items,count=count,page=page,pages=pages,status=status)


@bp.route('/ekle',methods=['GET','POST'])
@login_required
def add():
    own_member = member_for_user(g.user.id)
    if g.user.role!='admin' and own_member is None:
        abort(403)
    data = request.form if request.method=='POST' else request.args
    error = None
    if request.method=='POST':
        try:
            book_id = data.get('book_id','')
            member_id = data.get('member_id','') if g.user.role=='admin' else own_member
            reservation_service.create_reservation(book_id,member_id,g.user.id)
        except reservation_service.ReservationValidationError as problem:
            error = str(problem)
        else:
            flash('Rezervasyon oluşturuldu; kronolojik bekleme sırasına eklendiniz.','success')
            return redirect(url_for('reservations.index'))
    books,members = reservation_service.choices()
    return render_template('reservation_form.html',data=data,books=books,members=members,error=error),422 if error else 200


@bp.post('/<int:reservation_id>/iptal')
@login_required
def cancel(reservation_id):
    try:
        reservation_service.cancel_reservation(reservation_id,g.user.id,member_for_user(g.user.id),g.user.role=='admin')
    except LookupError:
        abort(404)
    except reservation_service.ReservationValidationError as problem:
        return render_template('reservation_conflict.html',message=str(problem)),409
    flash('Rezervasyon iptal edildi.','success')
    return redirect(url_for('reservations.index'))

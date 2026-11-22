"""Üye yönetimi yalnızca yöneticiye açıktır."""
from flask import Blueprint,abort,flash,g,redirect,render_template,request,url_for
from database import get_db
from security import role_required
from services import member_service
from services.validation import requested_page

bp=Blueprint('members',__name__,url_prefix='/uyeler')


@bp.get('')
@role_required('admin')
def index():
    query=request.args.get('q','').strip()
    status=request.args.get('status','all')
    if len(query)>200 or status not in ('all','active','inactive'):
        abort(400)
    page=requested_page(request.args.get('page',1))
    rows,count,page,pages=member_service.search_members(query,status,page)
    return render_template('members.html',rows=rows,count=count,page=page,pages=pages,query=query,status=status)


def member_form(member_id=None):
    member=member_service.get_member(member_id) if member_id else None
    if member_id and member is None:
        abort(404)
    data=request.form if request.method=='POST' else dict(member) if member else {'member_type':'student'}
    linked_account=get_db().execute('SELECT username FROM users WHERE id=?',(member['user_id'],)).fetchone() if member and member['user_id'] else None
    error=None
    if request.method=='POST':
        try:
            member_service.save_member(data,g.user.id,member_id)
        except member_service.MemberValidationError as problem:
            error=str(problem)
        except LookupError:
            abort(404)
        else:
            flash('Üye bilgileri kaydedildi.','success')
            return redirect(url_for('members.index'))
    return render_template('member_form.html',data=data,member=member,linked_account=linked_account,error=error),422 if error else 200


@bp.route('/ekle',methods=['GET','POST'])
@role_required('admin')
def add():
    return member_form()


@bp.route('/<int:member_id>/duzenle',methods=['GET','POST'])
@role_required('admin')
def edit(member_id):
    return member_form(member_id)


@bp.post('/<int:member_id>/durum')
@role_required('admin')
def status(member_id):
    if request.form.get('active') not in ('0','1'):
        abort(400)
    try:
        member_service.set_active(member_id,request.form['active']=='1',g.user.id)
    except LookupError:
        abort(404)
    flash('Üyelik durumu güncellendi.','success')
    return redirect(url_for('members.index'))


@bp.get('/<int:member_id>')
@role_required('admin')
def history(member_id):
    member=member_service.get_member(member_id)
    if member is None:
        abort(404)
    loans=get_db().execute('SELECT l.*,b.title FROM loans l JOIN books b ON b.id=l.book_id WHERE member_id=? ORDER BY l.id DESC LIMIT 50',(member_id,)).fetchall()
    return render_template('member_history.html',member=member,loans=loans)

"""SQLite kaynaklı, rol kapsamına göre filtrelenmiş panel verileri."""
from datetime import timedelta
from database import get_db
from services.loan_service import today
from services.notification_service import member_for_user, unread_count


def dashboard_data(user):
    db = get_db()
    admin = user.role == 'admin'
    member_id = member_for_user(user.id) if not admin else None
    def scalar(sql, params=()):
        return db.execute(sql,params).fetchone()[0]
    scope = '' if admin else ' AND member_id=?'
    args = () if admin else (member_id if member_id is not None else -1,)
    active = scalar('SELECT COUNT(*) FROM loans WHERE returned_on IS NULL'+scope,args)
    overdue = scalar('SELECT COUNT(*) FROM loans WHERE returned_on IS NULL AND due_on<?'+scope,(today().isoformat(),*args))
    waiting = scalar("SELECT COUNT(*) FROM reservations WHERE status IN ('active','notified')"+scope,args)
    if admin:
        cards = [
            {'key':'books','label':'Toplam kitap','value':scalar('SELECT COUNT(*) FROM books'),'icon':'book','hint':'Katalogdaki farklı kayıtlar'},
            {'key':'available','label':'Mevcut kitap','value':scalar('SELECT COUNT(*) FROM book_inventory WHERE available_copies>0'),'icon':'check','hint':'En az bir adet / lisans mevcut'},
            {'key':'members','label':'Kayıtlı üye','value':scalar('SELECT COUNT(*) FROM members'),'icon':'users','hint':'Aktif ve pasif üyeler'},
        ]
    else:
        cards = [{'key':'notifications','label':'Okunmamış bildirim','value':unread_count(user.id),'icon':'bell','hint':'Yalnızca hesabınıza ait'}]
    cards.extend([
        {'key':'active','label':'Aktif ödünç' if admin else 'Aktif ödünçlerim','value':active,'icon':'loans','hint':'Henüz iade edilmemiş'},
        {'key':'overdue','label':'Geciken ödünç' if admin else 'Geciken ödünçlerim','value':overdue,'icon':'warning','hint':'Son teslim tarihi geçmiş'},
        {'key':'reservations','label':'Bekleyen rezervasyon','value':waiting,'icon':'calendar','hint':'Bekliyor veya bildirim gönderildi'},
    ])
    first = today().replace(day=1)
    months=[]
    for _ in range(6):
        months.append(first)
        first=(first-timedelta(days=1)).replace(day=1)
    months.reverse()
    names=['Oca','Şub','Mar','Nis','May','Haz','Tem','Ağu','Eyl','Eki','Kas','Ara']
    series=[]
    for month in months:
        key=month.strftime('%Y-%m')
        series.append({'label':f'{names[month.month-1]} {month.year}',
                       'borrowed':scalar("SELECT COUNT(*) FROM loans WHERE substr(borrowed_on,1,7)=? AND borrowed_on<=?"+scope,(key,today().isoformat(),*args)),
                       'returned':scalar("SELECT COUNT(*) FROM loans WHERE substr(returned_on,1,7)=? AND returned_on<=?"+scope,(key,today().isoformat(),*args))})
    chart_max=max(1,max(max(item['borrowed'],item['returned']) for item in series))
    types=[{'label':'Fiziksel Kitap','count':scalar("SELECT COUNT(*) FROM books WHERE book_type='physical'"),'class':'physical'},
           {'label':'Elektronik Kitap','count':scalar("SELECT COUNT(*) FROM books WHERE book_type='ebook'"),'class':'ebook'},
           {'label':'Sesli Kitap','count':scalar("SELECT COUNT(*) FROM books WHERE book_type='audio'"),'class':'audio'}]
    type_total=sum(item['count'] for item in types)
    offset = 0
    for item in types:
        item['percent'] = round(item['count']*100/type_total,2) if type_total else 0
        item['offset'] = offset
        offset += item['percent']
    if admin:
        activities=db.execute('SELECT action,details,created_at FROM activity_logs ORDER BY created_at DESC,id DESC LIMIT 7').fetchall()
    else:
        # Üye başka kişilerin işlem günlüğünü görmez; kendi gerçek ödünç olaylarını görür.
        activities=db.execute("SELECT 'loan_created' AS action,b.title AS details,l.borrowed_on AS created_at FROM loans l JOIN books b ON b.id=l.book_id WHERE l.member_id=? UNION ALL SELECT 'loan_returned',b.title,l.returned_on FROM loans l JOIN books b ON b.id=l.book_id WHERE l.member_id=? AND l.returned_on IS NOT NULL ORDER BY created_at DESC LIMIT 7",(member_id,member_id)).fetchall()
    overdue_rows=db.execute('SELECT l.id,l.due_on,b.title,m.full_name FROM loans l JOIN books b ON b.id=l.book_id JOIN members m ON m.id=l.member_id WHERE l.returned_on IS NULL AND l.due_on<?'+('' if admin else ' AND l.member_id=?')+' ORDER BY l.due_on,l.id LIMIT 5',(today().isoformat(),*args)).fetchall()
    for_demo=bool(db.execute("SELECT 1 FROM activity_logs WHERE action='demo_seed' LIMIT 1").fetchone())
    return {'cards':cards,'series':series,'chart_max':chart_max,'types':types,'type_total':type_total,
            'activities':activities,'overdue_rows':overdue_rows,'demo_data':for_demo,'today':today()}

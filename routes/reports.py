"""Yetkili rapor önizleme ve dışa aktarma."""
from flask import Blueprint, abort, render_template, request, send_file

from security import role_required
from services import reports
from services.analytics import selected_period

bp = Blueprint('reports', __name__)
FORMATS = {
    'csv': (reports.csv_export, 'text/csv'),
    'xlsx': (reports.xlsx_export, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
    'pdf': (reports.pdf_export, 'application/pdf'),
}


@bp.get('/raporlar')
@role_required('admin')
def index():
    key = request.args.get('report', 'kitap')
    file_format = request.args.get('format', '')
    if key not in reports.SPECS or (file_format and file_format not in FORMATS):
        abort(400)
    try:
        period = selected_period(request.args)
    except ValueError as error:
        return render_template('reports.html', specs=reports.SPECS, key=key, error=str(error)), 422
    report = reports.build_report(key, period)
    if file_format:
        export, mimetype = FORMATS[file_format]
        response = send_file(export(report), mimetype=mimetype, as_attachment=True,
                             download_name=f'{key}-raporu.{file_format}')
        response.cache_control.no_store = True
        return response
    return render_template('reports.html', specs=reports.SPECS, key=key, report=report)

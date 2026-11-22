"""Eğitim sayfası için bağımlılıksız SVG UML sınıf diyagramları üretir."""
from pathlib import Path
from xml.sax.saxutils import escape
from xml.etree import ElementTree as ET

OUT=Path(__file__).resolve().parents[1]/'static'/'images'


def box(x,y,name,methods=(),abstract=False,w=220):
    title=escape(name)
    stereotype='<text x="%s" y="%s" class="st">«abstract»</text>'%(x+w/2,y+18) if abstract else ''
    title_y=y+36 if abstract else y+27
    methods_text=''.join(f'<text x="{x+12}" y="{y+62+i*17}" class="method">{escape(method)}</text>' for i,method in enumerate(methods))
    return f'<g><rect x="{x}" y="{y}" width="{w}" height="100" rx="7"/>{stereotype}<text x="{x+w/2}" y="{title_y}" class="title">{title}</text><path d="M{x} {y+44}H{x+w}" class="divider"/>{methods_text}</g>'


def edge(path,label='',x=0,y=0,inherit=False):
    return f'<path d="{path}" class="edge" marker-end="url(#{"inherit" if inherit else "arrow"})"/>'+ (f'<text x="{x}" y="{y}" class="label">{escape(label)}</text>' if label else '')


def diagram(name,content):
    svg='''<svg xmlns="http://www.w3.org/2000/svg" width="1040" height="430" viewBox="0 0 1040 430" role="img">
<defs><marker id="inherit" markerWidth="12" markerHeight="12" refX="11" refY="6" orient="auto"><path d="M1 1L11 6 1 11Z" fill="#f8fbfd" stroke="#52788c"/></marker><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M1 1L7 4 1 7" fill="none" stroke="#52788c"/></marker></defs>
<style>rect{fill:#fff;stroke:#bdcfda;stroke-width:1.2}.title{font:600 13px system-ui;fill:#17374b;text-anchor:middle}.st{font:10px system-ui;fill:#138572;text-anchor:middle}.method{font:11px monospace;fill:#506a7e}.divider{stroke:#dce6ed;stroke-width:1}.edge{fill:none;stroke:#52788c;stroke-width:1.4}.label{font:10px system-ui;fill:#138572;text-anchor:middle}</style><rect width="1040" height="430" fill="#f8fbfd" stroke="none"/>
'''+content+'</svg>'
    OUT.mkdir(parents=True,exist_ok=True)
    # SVG sunum nitelikleri: CSP altında satır içi stil gerektirmez.
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    root=ET.fromstring(svg)
    attrs={
        'title':{'font-family':'system-ui','font-size':'13','font-weight':'600','fill':'#17374b','text-anchor':'middle'},
        'st':{'font-family':'system-ui','font-size':'10','fill':'#138572','text-anchor':'middle'},
        'method':{'font-family':'monospace','font-size':'11','fill':'#506a7e'},
        'divider':{'stroke':'#dce6ed','stroke-width':'1','fill':'none'},
        'edge':{'fill':'none','stroke':'#52788c','stroke-width':'1.4'},
        'label':{'font-family':'system-ui','font-size':'10','fill':'#138572','text-anchor':'middle'},
    }
    for element in root.iter():
        if element.tag.endswith('rect'):
            for key,value in {'fill':'#fff','stroke':'#bdcfda','stroke-width':'1.2'}.items():
                element.attrib.setdefault(key,value)
        element.attrib.update(attrs.get(element.get('class'),{}))
    for child in list(root):
        if child.tag.endswith('style'):
            root.remove(child)
    ET.ElementTree(root).write(OUT/name,encoding='utf-8',xml_declaration=True)


diagram('uml-factory.svg',
    box(150,20,'BookCreator',['+ create_book() : Book','+ prepare_book() : Book'],True)+
    box(670,20,'Book',['+ validate_details()','+ type_label'],True)+
    box(10,220,'PhysicalBookCreator',['+ create_book()'],w=155)+
    box(180,220,'EBookCreator',['+ create_book()'],w=155)+
    box(350,220,'AudioBookCreator',['+ create_book()'],w=155)+
    box(535,220,'PhysicalBook',['+ validate_details()'],w=155)+
    box(705,220,'EBook',['+ validate_details()'],w=155)+
    box(875,220,'AudioBook',['+ validate_details()'],w=155)+
    edge('M87 220V165H260V120',inherit=True)+edge('M257 220V120',inherit=True)+edge('M427 220V165H260V120',inherit=True)+
    edge('M612 220V165H780V120',inherit=True)+edge('M782 220V120',inherit=True)+edge('M952 220V165H780V120',inherit=True)+
    edge('M370 70H670','ürün sözleşmesini kullanır',520,59)+
    edge('M87 320V351H612V320')+edge('M257 320V377H782V320')+edge('M427 320V403H952V320'))

diagram('uml-adapter.svg',
    box(410,15,'BookDataProvider',['+ search_page()','+ get_book()'],True)+
    box(255,170,'GoogleBooksAdapter',['+ adapt(item)','- api : GoogleBooksAPI'])+
    box(565,170,'OpenLibraryAdapter',['+ adapt(work_id, doc, isbn)','- api : OpenLibraryAPI'])+
    box(15,170,'GoogleBooksAPI',['+ search_volumes(q)','+ get_volume(id)'])+
    box(805,170,'OpenLibraryAPI',['+ search_works(query)','+ get_work(id)'])+
    box(410,315,'BookImportData',['title / author / isbn','+ to_form()'])+
    edge('M365 170V145H520V115',inherit=True)+edge('M675 170V145H520V115',inherit=True)+
    edge('M255 220H235')+edge('M785 220H805')+
    edge('M365 270V365H410')+edge('M675 270V365H630'))

diagram('uml-strategy.svg',
    box(65,30,'PenaltyCalculator',['+ set_strategy(strategy)','+ calculate(due,return)'])+
    box(620,30,'PenaltyStrategy',['+ calculate(days)'],True)+
    box(65,270,'StudentPenalty',['2 TL / gün','+ calculate(days)'])+
    box(410,270,'TeacherPenalty',['1 TL / gün','+ calculate(days)'])+
    box(755,270,'StandardPenalty',['5 TL / gün','+ calculate(days)'])+
    edge('M285 80H620','değiştirilebilir strateji',453,68)+
    edge('M175 270V210H730V130',inherit=True)+edge('M520 270V210H730V130',inherit=True)+edge('M865 270V210H730V130',inherit=True))

diagram('uml-observer.svg',
    box(50,15,'Subject',['+ attach() / detach()','+ notify()'],True)+
    box(770,15,'Observer',['+ update(book_id,title)'],True)+
    box(50,190,'BookAvailabilitySubject',['- observers','+ notify()'])+
    box(770,190,'MemberObserver',['- reservation_id','+ update(book_id,title)'])+
    box(410,315,'NotificationService',['+ publish_availability()','+ notify_reserved_member()'])+
    edge('M160 190V115',inherit=True)+edge('M880 190V115',inherit=True)+
    edge('M270 240H770','abone / update çağrısı',520,228)+
    edge('M880 290V365H630','mesajı kaydeder',740,354)+edge('M410 365H160V290','SQLite abonelerini yükler',280,354))

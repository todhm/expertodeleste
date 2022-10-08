from dataparser.htmlparser import make_inline_style

def test_html_parser():
    with open('datacollections/testcase.html') as f:
        html_string = f.read()

    with open('datacollections/teststyle.css') as f:
        html_style = f.read()

    total_html = f"{html_string}<style>{html_style}</style>"    
    with open('datacollections/newhtml.html', 'w') as f:
        f.write(make_inline_style(total_html))
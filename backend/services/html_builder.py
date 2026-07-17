from html import escape


def heading(text: str, level: int = 3):
    return f"<h{level}>{escape(str(text))}</h{level}>"


def paragraph(text: str):
    return f"<p>{escape(str(text))}</p>"


def bold(text: str):
    return f"<b>{escape(str(text))}</b>"


def line_break():
    return "<br>"


def horizontal_rule():
    return "<hr>"


def hyperlink(text: str, url: str, new_tab=True):

    target = ' target="_blank"' if new_tab else ""

    return (
        f'<a href="{escape(url)}"{target}>'
        f'{escape(text)}</a>'
    )


def image(url: str,
          width="100%",
          border_radius="8px"):

    return (
        f'<img src="{escape(url)}" '
        f'style="max-width:{width};'
        f'border-radius:{border_radius};" />'
    )


def unordered_list(items):

    html = "<ul>"

    for item in items:
        html += f"<li>{item}</li>"

    html += "</ul>"

    return html


def ordered_list(items):

    html = "<ol>"

    for item in items:
        html += f"<li>{item}</li>"

    html += "</ol>"

    return html


def table(rows):

    """
    rows =

    [

        ("Current Price","1450"),

        ("PE Ratio","22.5")

    ]

    """

    html = """
    <table border="1"
           cellspacing="0"
           cellpadding="6"
           style="border-collapse:collapse;width:100%;">
    """

    for key, value in rows:

        html += f"""
        <tr>
            <th align="left">{escape(str(key))}</th>
            <td>{value}</td>
        </tr>
        """

    html += "</table>"

    return html


def card(title, body):

    return f"""
    <div
    style="
        border:1px solid #ddd;
        border-radius:8px;
        padding:12px;
        margin-bottom:10px;
    ">

        <h4>{escape(str(title))}</h4>

        {body}

    </div>
    """


def divider():
    return "<br><hr><br>"
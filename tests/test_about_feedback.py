import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import critical
from critical_pages import render_critical
from pages import render_pages

ROOT = Path(__file__).resolve().parents[1]
LINK = 'href="about.html#feedback" data-i18n="footerFeedback">About and feedback</a>'
ISSUE = 'https://github.com/AlejandroRenalias/shortage-radar/issues/new?template=error-report.yml'


def critical_pages():
    data = {'eu': critical.load_eu_list(), 'rows': [], 'counts': critical.counts([]), 'history': {}, 'archive_start': '2026-09-15', 'snapshot_date': '2026-11-23', 'source_metadata': {}}
    return render_critical(data)


def test_the_footer_links_to_about_and_feedback_on_every_page_type():
    out = render_pages(749)
    out.update(critical_pages())
    assert {'index.html', 'shortages.html', 'medicine.html', 'medicines.html', 'trends.html', 'about.html', '404.html', 'critical.html', 'critical-methods.html'} <= set(out)
    for name, html in out.items():
        footer = html[html.index('<footer'):html.index('</footer>')]
        # The 404 page is served from any depth, so its links start at the site root.
        link = LINK.replace('href="about.html', 'href="/shortage-radar/about.html') if name == '404.html' else LINK
        assert footer.count(link) == 1, name


def test_the_about_page_has_the_short_text_in_both_languages_and_the_feedback_link():
    about = render_pages(749)['about.html']
    assert about.index('id="about-site"') < about.index('id="what-to-do"') and about.count('<details class="fold">') == 3
    assert f'href="{ISSUE}"' in about and 'id="feedback"' in about and 'mailto:' not in about
    js = (ROOT / 'site/i18n.js').read_text(encoding='utf-8')
    keys = set(re.findall(r'data-i18n="((?:about(?:Short|Purpose|Indep|Not|Src|Shows|Lim)|feedback|footerFeedback)\w*)"', about + render_pages(749)['index.html']))
    assert len(keys) >= 30
    for key in keys:
        assert len(re.findall(rf'^    {key}: ', js, re.M)) == 2, key   # once in English and once in Finnish


def test_the_issue_template_asks_for_page_link_problem_and_source_and_no_email():
    text = (ROOT / '.github/ISSUE_TEMPLATE/error-report.yml').read_text(encoding='utf-8')
    for label in ('Page link', 'What is wrong', 'Source'):
        assert f'label: {label}\n' in text
    assert '@' not in text and 'mailto' not in text
    assert not (ROOT / '.github/ISSUE_TEMPLATE/data-problem.yml').exists()


def test_the_about_text_makes_the_three_statements_and_no_stock_or_safety_claim():
    js = (ROOT / 'site/i18n.js').read_text(encoding='utf-8')
    lines = [l for l in js.splitlines() if re.match(r'    (aboutShortTitle|aboutPurpose|aboutIndep|aboutNot\d|aboutNotTitle|aboutSrc\w*|aboutShows\w*|aboutLim\d|aboutLimTitle|feedback\w*):', l)]
    assert len(lines) == 2 * 30
    for line in lines:
        assert not re.search(r'\b(safe|safely|suitable|in stock)\b|turvallinen|sopiva', line, re.I), line
    assert 'unavailable everywhere' in js and 'not necessarily available' in js and 'not medical advice' in js


def test_the_footer_and_about_text_wrap_long_links_and_do_not_scroll_sideways():
    css = (ROOT / 'site/style.css').read_text(encoding='utf-8')
    assert '.foot a,.foot p{overflow-wrap:anywhere}' in css and '.about-layout .prose{overflow-wrap:anywhere}' in css

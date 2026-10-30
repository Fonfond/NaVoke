from pathlib import Path


def test_utils_loaded_before_admin():
    html = Path('frontend/pages/admin-panel.html').read_text(encoding='utf-8')
    assert html.index('/static/js/utils.js') < html.index('/static/js/admin.js')


def test_utils_loaded_before_order_detail():
    html = Path('frontend/pages/order-detail.html').read_text(encoding='utf-8')
    assert html.index('/static/js/utils.js') < html.index('/static/js/order-detail.js')


def test_escape_helper_covers_all_html_specials():
    source = Path('frontend/js/utils.js').read_text(encoding='utf-8')
    for char in ('&', '<', '>', '"', "'"):
        assert f"'{char}'" in source or f'"{char}"' in source


def test_no_token_logging_in_api():
    source = Path('frontend/js/api.js').read_text(encoding='utf-8')
    assert 'console.log(result.access' not in source
    assert 'console.log(result.refresh' not in source
